import jen.consts as consts

from .protocol import *
from .tools import *

import jen.globals as gb


class ClientLikeRole(PacketOrigin, DiffOrigin):

    def __init__(self):
        PacketOrigin.__init__(self)
        DiffOrigin.__init__(self)

        self.diff_packet_type = MarshalDiffPacket

        self.watching: set[str] = set(["", "*"])

        self.conn_id: str = "(unknown)"
        self.state: int = 0  # 0 = Registering, 1 = Running, 2 = Stopped

    def _sync_exact_match(self, diff: Diff, packet: Packet, early: bool = False):
        # The diff must be recorded in the diff_queue even if the client is not ready to receive it
        if early:
            self.ignored_diff_id.add(diff.diff_id)
        elif diff.diff_id in self.ignored_diff_id:
            # It is possible to handle ignored diffs here since an upstream doesn't have its own filter
            self.ignored_diff_id.remove(diff.diff_id)
            return

        if self.state == 0:
            return

        for w in self.watching:
            if diff.match(w):
                self.write(packet)
                break

    def update_watch(self):
        gb.write("conn." + self.conn_id + ".watch", list(self.watching))


class UpstreamRole(ClientLikeRole):

    def __init__(self):
        ClientLikeRole.__init__(self)

    def read(self, in_raw: bytes):
        packet = self._decode_packet(in_raw, [HelloD2UPacket, DiffPacket, MarshalDiffPacket, DebugMessageD2UPacket])
        packet_class = type(packet)

        if packet_class is HelloD2UPacket:
            logger.info("Send Identity to \"%s\" gateway" % self.conn_id)

            self.write(GatewayIdentityU2DPacket().encode(self.conn_id))
        elif packet_class is DiffPacket or packet_class is MarshalDiffPacket:
            conn_profile_path = "conn." + self.conn_id
            watcher_path = conn_profile_path + ".watch"

            if watcher_path.startswith(packet.path):
                old_watchers = set(gb.read(watcher_path) or [])

                gb.write(packet.path, packet.change, False, self)

                self.watching = set(gb.read(watcher_path) or [])
                for watcher in self.watching - old_watchers:
                    if not watcher.endswith("*"):
                        self.write(self.diff_packet_type().encode(watcher, gb.read(watcher)))

                if gb.read(conn_profile_path) is None:
                    self.state = 2
            else:
                gb.write(packet.path, packet.change, False, self)
        elif packet_class is DebugMessageD2UPacket:
            print(CustomFormatter.green + packet.message + CustomFormatter.reset, end="")

        if self.state == 0 and packet_class is not HelloD2UPacket:
            self.state = 1


class DownstreamRole(ClientLikeRole):

    def __init__(self):
        ClientLikeRole.__init__(self)

    def read(self, in_raw: bytes):
        packet = self._decode_packet(in_raw, [GatewayIdentityU2DPacket, DiffPacket, MarshalDiffPacket])
        packet_class = type(packet)

        if packet_class is GatewayIdentityU2DPacket and self.state == 0:
            self.conn_id = packet.conn_id
            self.state = 1
            if "*" not in self.watching:
                self.watching.add("conn." + self.conn_id)

            gb.write("conn." + self.conn_id, {
                "available": True,
                "worker_name": gb.current_worker.display_name if gb.current_worker else "(unknown)",
                "watch": list(self.watching)
            })

            logger.info("Registered \"%s\" gateway", self.conn_id)
        elif packet_class is DiffPacket or packet_class is MarshalDiffPacket:
            gb.write(packet.path, packet.change, False, self)


class ServerLikeRole(DiffOrigin):

    def __init__(self):
        self.connections: dict[any, UpstreamRole] = {}

    def _sync_exact_match(self, diff: Diff, packet: Packet, early: bool = False):
        if early:
            # If and only if a write() call is made, the diff is recorded by the server
            self.ignored_diff_id.add(diff.diff_id)

        [self.connections[k]._sync_exact_match(diff, packet, False) for k in list(self.connections)]


class Gateway(DiffOrigin):

    def __init__(self):
        DiffOrigin.__init__(self)

        self.last_handled_diff_id: int = 0
        self.started: bool = False
        self.diff_packet_type = MarshalDiffPacket

    def _filter_final_sync(self) -> list[Diff]:
        all_diffs = gb.diff_queue

        diffs: list[Diff] = []
        last_handled = None
        for i in range(consts.DIFF_QUEUE_SIZE, 0, -1):
            diff = all_diffs[i - 1]
            if diff.diff_id == self.last_handled_diff_id or diff.diff_id == 0:
                break
            if last_handled is None:
                last_handled = diff.diff_id
            if diff.diff_id in self.ignored_diff_id:
                self.ignored_diff_id.remove(diff.diff_id)
                continue
            diffs.insert(0, diff)

        if last_handled is not None:
            self.last_handled_diff_id = last_handled

        return diffs

    def _sync(self):
        for f in self._filter_final_sync():
            packet = self.diff_packet_type().encode_diff(f)
            self._sync_exact_match(f, packet)

    def _sync_thread(self):
        while self.started:
            self._sync()
            with gb.sync_condition:
                gb.sync_condition.wait()

    def start(self):
        pass

    def stop(self):
        self.started = False
        with gb.sync_condition:
            gb.sync_condition.notify_all()


class GatewayManager:

    def spin(self):
        pass


class WorkerController:

    def __init__(self, name: str, shared_data: dict):
        self.name = name
        self.display_name = ''.join(word.title() for word in name.split('_'))
        self.shared_data = shared_data
        self.managers: list[GatewayManager] = []
        self.clock: Optional[Clock] = None

        logger.info("Worker \"%s\" registered" % self.display_name)

    def init(self):
        gb.diff_queue = [Diff.placeholder()] * consts.DIFF_QUEUE_SIZE
        gb.sync_condition = threading.Condition()
        gb.share = self.shared_data
        gb.current_worker = self
        gb.gateways = []
        gb.early_gateways = []

        logger.name = self.display_name

        logger.info("Worker started on process %s" % os.getpid())

    def use_clock(self, frequency: int, busy_wait=False, offset=0.0004):
        self.clock = Clock(frequency, busy_wait, offset)
        return self.clock

    def use_serial_manager(self):
        from jen.tty import SerialConnectionManager

        m = SerialConnectionManager(self)
        self.managers.append(m)
        return m

    def spin(self):
        [m.spin() for m in self.managers]
        if self.clock is not None:
            self.clock.spin()
