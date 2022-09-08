import sys
sys.path.insert(1, './')

from jen import *
from multiprocessing import Pool, Process
import random
import pytest


def udp_thread(worker: WorkerController, attempts: int):
    worker.init()

    client = gb.start_gateway(UDPBroadcast("255.255.255.255", 7986))

    data = None

    for i in range(attempts):
        print("wait")
        for _ in range(10000):
            time.sleep(0.001)
            if gb.read("value_udpb") is not data:
                break
        
        data = gb.clone("value_udpb")
        data.reverse()
        gb.write("value_udpb", data)


def udp_main(data_size: int, attempts: int):
    gb.gateways = []
    
    gb.start_gateway(UDPBroadcast("255.255.255.255", 7986))

    p = Process(target=udp_thread, args=(WorkerController("0", gb.share), attempts))
    p.start()

    time.sleep(0.1)

    for i in range(attempts):
        data = list(j for j in range(data_size))
        gb.write("value_udpb", data)

        print("sent")
        for _ in range(10000):
            time.sleep(0.001)
            if gb.read("value_udpb") is not data:
                break
        
        data.reverse()
        assert data == gb.read("value_udpb")
        print("round", i)
            

    p.kill()

    gb.gateways[0].stop()

    print("Done")


def test_udpb_signal_process():
    udp_main(2048 // 5 - 8, 500)  # (2048 // 5 - 8) = 2023 packet size


def test_udpb_start_stop_and_error_handling():
    broadcast = gb.start_gateway(UDPBroadcast("255.255.255.255", 7986))

    # useless
    broadcast.start()
    time.sleep(0.1)
    try:
        broadcast.s.shutdown(socket.SHUT_RDWR)
    except:
        pass
    time.sleep(0.1)
    broadcast.stop()


class MockBroadcast(UDPBroadcast):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._sync_count = 0
        self._write_count = 0

    def _sync_exact_match(self, diff: Diff, packet: Packet, early: bool = False):
        UDPBroadcast._sync_exact_match(self, diff, packet, early)
        self._sync_count += 1

    def write(self, packet: Packet):
        self._write_count += 1


def test_udpb_sync_method():
    b = MockBroadcast("255.255.255.255", 7986)
    gb.gateways = [b]

    b.started = True

    assert b._sync_count == 0
    assert b._write_count == 0
    assert b.last_handled_diff_id == 0
    assert b.ignored_diff_id == set()

    gb.diff_queue = [Diff(i, "", "") for i in range(consts.DIFF_QUEUE_SIZE)]
    b._sync()

    assert b._sync_count == consts.DIFF_QUEUE_SIZE - 1
    assert b._write_count == consts.DIFF_QUEUE_SIZE - 1
    assert b.last_handled_diff_id == gb.diff_queue[-1].diff_id
    assert b.ignored_diff_id == set()

    gb.write("change", 1)
    b._sync()

    assert b._sync_count == consts.DIFF_QUEUE_SIZE
    assert b._write_count == consts.DIFF_QUEUE_SIZE
    assert b.ignored_diff_id == set()

    gb.write("change", 2)
    gb.write("change", 3)
    gb.write("change", 4)
    b._sync()

    assert b._sync_count == consts.DIFF_QUEUE_SIZE + 3
    assert b._write_count == consts.DIFF_QUEUE_SIZE + 3
    assert b.ignored_diff_id == set()

    gb.early_gateways = [b]

    gb.write("change", 5)

    assert b._sync_count == consts.DIFF_QUEUE_SIZE + 4
    assert b._write_count == consts.DIFF_QUEUE_SIZE + 4
    assert b.ignored_diff_id == set([gb.diff_queue[-1].diff_id])

    b._sync()

    gb.early_gateways = []

    assert b._sync_count == consts.DIFF_QUEUE_SIZE + 4
    assert b._write_count == consts.DIFF_QUEUE_SIZE + 4

    b.read(MarshalDiffBroadcastPacket().encode(1500, "anything", 1).data)
    b._sync()

    assert gb.read("anything") == 1
    assert b._sync_count == consts.DIFF_QUEUE_SIZE + 4
    assert b._write_count == consts.DIFF_QUEUE_SIZE + 4

    b.read(MarshalDiffBroadcastPacket().encode(1501, "something", 2).data)
    b._sync()

    assert b._sync_count == consts.DIFF_QUEUE_SIZE + 4
    assert b._write_count == consts.DIFF_QUEUE_SIZE + 4
