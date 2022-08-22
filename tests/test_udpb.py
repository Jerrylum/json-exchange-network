import sys
sys.path.insert(1, './')

from jen import *
from multiprocessing import Pool, Process
import random
import pytest


def udp_thread(worker: WorkerController, attempts: int):
    worker.init()

    client = gb.join_broadcast(("255.255.255.255", 7986))

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
    
    gb.join_broadcast(("255.255.255.255", 7986))

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
