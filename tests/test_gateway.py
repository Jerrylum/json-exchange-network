import sys
sys.path.insert(1, './')

from jen import *
import random
import pytest


def test_gateway_filter_sync():
    gb.diff_queue = [Diff(i, "", "") for i in range(consts.DIFF_QUEUE_SIZE)]

    g = Gateway()
    assert g._filter_final_sync() == gb.diff_queue[1:] # zero does not count
    assert g.last_handled_diff_id == consts.DIFF_QUEUE_SIZE - 1

    assert g._filter_final_sync() == []
    assert g.last_handled_diff_id == consts.DIFF_QUEUE_SIZE - 1

    assert g._filter_final_sync() == []
    assert g.last_handled_diff_id == consts.DIFF_QUEUE_SIZE - 1

    g.last_handled_diff_id = 30

    assert g._filter_final_sync() == gb.diff_queue[31:] # skip synced diffs
    assert g.last_handled_diff_id == consts.DIFF_QUEUE_SIZE - 1

    assert g._filter_final_sync() == []
    assert g.last_handled_diff_id == consts.DIFF_QUEUE_SIZE - 1

    g.last_handled_diff_id = 30
    g.ignored_diff_id = [33]

    assert g._filter_final_sync() == gb.diff_queue[31:33] + gb.diff_queue[34:] # skip ignored diffs
    assert g.last_handled_diff_id == consts.DIFF_QUEUE_SIZE - 1

    gb.diff_queue = [Diff(i, "", "") for i in range(1000, 1000 + consts.DIFF_QUEUE_SIZE)]

    assert g._filter_final_sync() == gb.diff_queue # recover from outdated situation
    assert g.last_handled_diff_id == gb.diff_queue[-1].diff_id


class MockDownstreamRole(Gateway, DownstreamRole):

    def __init__(self):
        self._sync_count = 0
        self._write_count = 0
        Gateway.__init__(self)
        DownstreamRole.__init__(self)

    def _sync_exact_match(self, diff: Diff, packet: Packet, early: bool = False):
        ClientLikeRole._sync_exact_match(self, diff, packet, early)
        self._sync_count += 1

    def write(self, packet: Packet):
        self._write_count += 1


def test_client_sync_matched():
    c = MockDownstreamRole()
    gb.gateways = [c]

    c.started = True
    c.state = 1

    assert c._sync_count == 0
    assert c._write_count == 0
    assert c.last_handled_diff_id == 0
    assert c.ignored_diff_id == set()

    gb.diff_queue = [Diff(i, "", "") for i in range(consts.DIFF_QUEUE_SIZE)]
    c._sync()

    assert c._sync_count == consts.DIFF_QUEUE_SIZE - 1
    assert c._write_count == consts.DIFF_QUEUE_SIZE - 1
    assert c.last_handled_diff_id == gb.diff_queue[-1].diff_id
    assert c.ignored_diff_id == set()

    gb.write("change", 1)
    c._sync()

    assert c._sync_count == consts.DIFF_QUEUE_SIZE
    assert c._write_count == consts.DIFF_QUEUE_SIZE
    assert c.ignored_diff_id == set()

    gb.write("change", 2)
    gb.write("change", 3)
    gb.write("change", 4)
    c._sync()

    assert c._sync_count == consts.DIFF_QUEUE_SIZE + 3
    assert c._write_count == consts.DIFF_QUEUE_SIZE + 3
    assert c.ignored_diff_id == set()

    gb.early_gateways = [c]

    gb.write("change", 5)

    assert c._sync_count == consts.DIFF_QUEUE_SIZE + 4
    assert c._write_count == consts.DIFF_QUEUE_SIZE + 4
    assert c.ignored_diff_id == set([gb.diff_queue[-1].diff_id])

    c._sync()

    gb.early_gateways = []

    assert c._sync_count == consts.DIFF_QUEUE_SIZE + 4
    assert c._write_count == consts.DIFF_QUEUE_SIZE + 4

    c.read(DiffPacket().encode("anything", 1).data)
    c._sync()

    assert gb.read("anything") == 1
    assert c._sync_count == consts.DIFF_QUEUE_SIZE + 4
    assert c._write_count == consts.DIFF_QUEUE_SIZE + 4

    c.watching = set(["any*"])
    c.update_watch()
    c._sync()

    assert c._sync_count == consts.DIFF_QUEUE_SIZE + 5
    assert c._write_count == consts.DIFF_QUEUE_SIZE + 4

    gb.write("anything", 2)
    c._sync()

    assert c._sync_count == consts.DIFF_QUEUE_SIZE + 6
    assert c._write_count == consts.DIFF_QUEUE_SIZE + 5
    
    gb.write("change", 5)
    c._sync()

    assert c._sync_count == consts.DIFF_QUEUE_SIZE + 6
    assert c._write_count == consts.DIFF_QUEUE_SIZE + 5


class MockUpstreamRole(UpstreamRole):

    def __init__(self):
        self._sync_count = 0
        self._write_count = 0
        UpstreamRole.__init__(self)

    def _sync_exact_match(self, diff: Diff, packet: Packet, early: bool = False):
        ClientLikeRole._sync_exact_match(self, diff, packet, early)
        self._sync_count += 1

    def write(self, packet: Packet):
        self._write_count += 1


class MockServerLikeRole(Gateway, ServerLikeRole):

    def __init__(self):
        self._sync_count = 0
        Gateway.__init__(self)
        ServerLikeRole.__init__(self)

    def _sync_exact_match(self, diff: Diff, packet: Packet, early: bool = False):
        ServerLikeRole._sync_exact_match(self, diff, packet, early)
        self._sync_count += 1


def test_server_sync_matched():
    s = MockServerLikeRole()
    u1 = MockUpstreamRole()
    u2 = MockUpstreamRole()

    s.connections["any1"] = u1
    s.connections["any2"] = u2

    u1.state = 1
    u2.state = 1

    assert s._sync_count == 0
    assert s.last_handled_diff_id == 0
    assert s.ignored_diff_id == set()
    assert u1._sync_count == 0
    assert u1._write_count == 0
    assert u1.ignored_diff_id == set()
    assert u2._sync_count == 0
    assert u2._write_count == 0
    assert u2.ignored_diff_id == set()

    gb.diff_queue = [Diff(i, "", "") for i in range(consts.DIFF_QUEUE_SIZE)]
    s._sync()

    assert s._sync_count == consts.DIFF_QUEUE_SIZE - 1
    assert s.last_handled_diff_id == gb.diff_queue[-1].diff_id
    assert s.ignored_diff_id == set()
    assert u1._sync_count == consts.DIFF_QUEUE_SIZE - 1
    assert u1._write_count == consts.DIFF_QUEUE_SIZE - 1
    assert u1.ignored_diff_id == set()
    assert u2._sync_count == consts.DIFF_QUEUE_SIZE - 1
    assert u2._write_count == consts.DIFF_QUEUE_SIZE - 1
    assert u2.ignored_diff_id == set()

    gb.write("change", 1)
    s._sync()

    assert s._sync_count == consts.DIFF_QUEUE_SIZE
    assert s.ignored_diff_id == set()
    assert u1._sync_count == consts.DIFF_QUEUE_SIZE
    assert u1._write_count == consts.DIFF_QUEUE_SIZE
    assert u1.ignored_diff_id == set()
    assert u2._sync_count == consts.DIFF_QUEUE_SIZE
    assert u2._write_count == consts.DIFF_QUEUE_SIZE
    assert u2.ignored_diff_id == set()

    gb.write("change", 2)
    gb.write("change", 3)
    gb.write("change", 4)
    s._sync()

    assert s._sync_count == consts.DIFF_QUEUE_SIZE + 3
    assert s.ignored_diff_id == set()
    assert u1._sync_count == consts.DIFF_QUEUE_SIZE + 3
    assert u1._write_count == consts.DIFF_QUEUE_SIZE + 3
    assert u1.ignored_diff_id == set()
    assert u2._sync_count == consts.DIFF_QUEUE_SIZE + 3
    assert u2._write_count == consts.DIFF_QUEUE_SIZE + 3
    assert u2.ignored_diff_id == set()

    gb.early_gateways = [s]

    gb.write("change", 5)

    assert s._sync_count == consts.DIFF_QUEUE_SIZE + 4
    assert s.ignored_diff_id == set([gb.diff_queue[-1].diff_id])
    assert u1._sync_count == consts.DIFF_QUEUE_SIZE + 4
    assert u1._write_count == consts.DIFF_QUEUE_SIZE + 4
    assert u1.ignored_diff_id == set()
    assert u2._sync_count == consts.DIFF_QUEUE_SIZE + 4
    assert u2._write_count == consts.DIFF_QUEUE_SIZE + 4
    assert u2.ignored_diff_id == set()

    s._sync()

    gb.early_gateways = []

    assert s._sync_count == consts.DIFF_QUEUE_SIZE + 4
    assert u1._sync_count == consts.DIFF_QUEUE_SIZE + 4
    assert u1._write_count == consts.DIFF_QUEUE_SIZE + 4
    assert u2._sync_count == consts.DIFF_QUEUE_SIZE + 4
    assert u2._write_count == consts.DIFF_QUEUE_SIZE + 4

    u1.read(DiffPacket().encode("anything", 1).data)
    s._sync()

    assert gb.read("anything") == 1
    assert s._sync_count == consts.DIFF_QUEUE_SIZE + 5
    assert u1._sync_count == consts.DIFF_QUEUE_SIZE + 5
    assert u1._write_count == consts.DIFF_QUEUE_SIZE + 4
    assert u2._sync_count == consts.DIFF_QUEUE_SIZE + 5
    assert u2._write_count == consts.DIFF_QUEUE_SIZE + 5

    u1.watching = set(["any*", "conn*"])
    u1.update_watch()
    s._sync()

    assert s._sync_count == consts.DIFF_QUEUE_SIZE + 6
    assert u1._sync_count == consts.DIFF_QUEUE_SIZE + 6
    assert u1._write_count == consts.DIFF_QUEUE_SIZE + 5
    assert u2._sync_count == consts.DIFF_QUEUE_SIZE + 6
    assert u2._write_count == consts.DIFF_QUEUE_SIZE + 6

    gb.write("anything", 2)
    s._sync()

    assert s._sync_count == consts.DIFF_QUEUE_SIZE + 7
    assert u1._sync_count == consts.DIFF_QUEUE_SIZE + 7
    assert u1._write_count == consts.DIFF_QUEUE_SIZE + 6
    assert u2._sync_count == consts.DIFF_QUEUE_SIZE + 7
    assert u2._write_count == consts.DIFF_QUEUE_SIZE + 7

    gb.write("change", 5)
    s._sync()

    assert s._sync_count == consts.DIFF_QUEUE_SIZE + 7
    assert u1._sync_count == consts.DIFF_QUEUE_SIZE + 7
    assert u1._write_count == consts.DIFF_QUEUE_SIZE + 6
    assert u2._sync_count == consts.DIFF_QUEUE_SIZE + 7
    assert u2._write_count == consts.DIFF_QUEUE_SIZE + 7


def test_abstract_methods():
    g = Gateway()
    g.start()
    g.stop()

    gm = GatewayManager()
    gm.spin()

    d = DiffOrigin()
    d._sync_exact_match(None, None, False)

    p = PacketOrigin()
    p.read(None)
    p.write(None)

    dp = DiffPacket().encode_diff(Diff.placeholder())
