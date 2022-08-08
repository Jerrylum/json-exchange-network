import consts

from core.protocol import *
from core.tools import *

import globals as gb


class GatewayClientLike(DiffOrigin):

    def __init__(self):
        DiffOrigin.__init__(self)

        self.watching: list[str] = ["*"]

        self.conn_id: str = "(unknown)"
        self.state: int = 0  # 0 = Registering, 1 = Running

    def _sync_exact_match(self, diff: Diff, packet: Packet, early: bool = False):
        if early:
            self.ignored_diff_id.add(diff.uuid)
        elif diff.uuid in self.ignored_diff_id:
            self.ignored_diff_id.remove(diff.uuid)
            return

        for w in self.watching:
            if diff.match(w):
                self.write(packet)
                break

    def read(self, in_raw: bytes):
        pass

    def write(self, packet: Packet):
        pass


class GatewayServerLike:

    def __init__(self):
        self.connections: dict[any, GatewayClientLike] = {}

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
            with gb.sync_condition:
                gb.sync_condition.wait()
            self._sync()


class GatewayManager:

    def spin(self):
        pass
