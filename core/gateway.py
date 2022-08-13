import consts

from core.protocol import *
from core.tools import *

import globals as gb


class ClientLikeRole(DiffOrigin):

    def __init__(self):
        DiffOrigin.__init__(self)

        self.diff_packet_type = MarshalDiffPacket

        self.watching: set[str] = set(["", "*"])

        self.conn_id: str = "(unknown)"
        self.state: int = 0  # 0 = Registering, 1 = Running

    def _sync_exact_match(self, diff: Diff, packet: Packet, early: bool = False):
        if early:
            self.ignored_diff_id.add(diff.uuid)
        elif diff.uuid in self.ignored_diff_id:
            self.ignored_diff_id.remove(diff.uuid)
            return

        if self.state == 0:
            return

        for w in self.watching:
            if diff.match(w):
                self.write(packet)
                break

    def read(self, in_raw: bytes):
        pass

    def write(self, packet: Packet):
        pass

    def update_watch(self):
        gb.write("conn." + self.conn_id + ".watch", list(self.watching))


class UpstreamRole(ClientLikeRole):

    def __init__(self):
        ClientLikeRole.__init__(self)

    def read(self, in_raw: bytes):
        packet_id, data = unpack(in_raw)

        available_packets = [HelloD2UPacket, DiffPacket, MarshalDiffPacket, DebugMessageD2UPacket]
        packet_class = [p for p in available_packets if p.PACKET_ID == packet_id][0]

        packet = packet_class().decode(data)

        if packet_class is HelloD2UPacket:
            logger.info("Send Identity to \"%s\" gateway" % self.conn_id)

            self.write(GatewayIdentityU2DPacket().encode(self.conn_id))
        elif packet_class is DiffPacket or packet_class is MarshalDiffPacket:
            watcher_path = "conn." + self.conn_id + ".watch"
            if watcher_path.startswith(packet.path):
                old_watchers = set(gb.read(watcher_path) or [])

                gb.write(packet.path, packet.change, False, self)

                self.watching = set(gb.read(watcher_path) or [])
                for watcher in self.watching - old_watchers:
                    if not watcher.endswith("*"):
                        self.write(self.diff_packet_type().encode(watcher, gb.read(watcher)))
            else:
                gb.write(packet.path, packet.change, False, self)
        elif packet_class is DebugMessageD2UPacket:
            print(CustomFormatter.green + packet.message + CustomFormatter.reset, end="")  # TODO

        if self.state == 0 and packet_class is not HelloD2UPacket:
            self.state = 1


class DownstreamRole(ClientLikeRole):

    def __init__(self):
        ClientLikeRole.__init__(self)

    def read(self, in_raw: bytes):
        packet_id, data = unpack(in_raw)

        available_packets = [GatewayIdentityU2DPacket, DiffPacket, MarshalDiffPacket]
        packet_class = [p for p in available_packets if p.PACKET_ID == packet_id][0]

        packet = packet_class().decode(data)

        if packet_class is GatewayIdentityU2DPacket and self.state == 0:
            self.conn_id = packet.conn_id
            self.state = 1
            if "*" not in self.watching:
                self.watching.add("conn." + self.conn_id)

            gb.write("conn." + self.conn_id, {
                "available": True,
                "worker_name": gb.current_worker.display_name if gb.current_worker else "(unknown)",
                "type": "udp",
                "watch": list(self.watching)
            })

            logger.info("Registered \"%s\" gateway", self.conn_id)
        elif packet_class is DiffPacket or packet_class is MarshalDiffPacket:
            gb.write(packet.path, packet.change, False, self)


class ServerLikeRole:

    def __init__(self):
        self.connections: dict[any, UpstreamRole] = {}

    def _sync_exact_match(self, diff: Diff, packet: Packet, early: bool = False):
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
            if diff.uuid == self.last_handled_diff_id or diff.uuid == 0:
                break
            if last_handled is None:
                last_handled = diff.uuid
            if diff.uuid in self.ignored_diff_id:
                self.ignored_diff_id.remove(diff.uuid)
                continue
            diffs.insert(0, diff)

        if last_handled is not None:
            self.last_handled_diff_id = last_handled

        return diffs

    def _sync_exact_match(self, diff: Diff, packet: Packet, early: bool = False):
        pass

    def _sync(self):
        for f in self._filter_final_sync():
            packet = self.diff_packet_type().encode(f.path, f.change)
            self._sync_exact_match(f, packet)

    def _sync_thread(self):
        while self.started:
            self._sync()
            with gb.sync_condition:
                gb.sync_condition.wait()


class GatewayManager:

    def spin(self):
        pass
