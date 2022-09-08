import sys
sys.path.insert(1, './')

from jen import *
from multiprocessing import Pool, Process
import random
import pytest


def ws_thread(params: tuple[WorkerController, int] ):
    worker, i = params
    worker.init()

    client = gb.start_gateway(WebsocketClient("127.0.0.1", 7985))
    client.watching = set(["value_ws"])

    ans = None

    for _ in range(100):
        time.sleep(0.1)
        ans = gb.read("value_ws." + str(i))
        if ans is not None:
            break

    client.stop()

    return ans


def ws_thread2(worker: WorkerController, i: list):
    worker.init()

    server = gb.start_gateway(WebsocketClient("127.0.0.1", 7985))
    time.sleep(1)
    gb.write("value_ws2", i)
    time.sleep(0.1)
    server.stop()


def ws_main(pool_size: int, attempts: int):
    gb.gateways = []
    
    the_pool = Pool(pool_size)
    expected = list([i for i in range(attempts)])

    gb.start_gateway(WebsocketServer("127.0.0.1", 7985))
    gb.write("value_ws", expected)
    
    with the_pool as p:
        actual = p.map(ws_thread, list([(WorkerController(str(i), { "conn": {} }), i) for i in range(attempts)]))

    [p.kill() for p in the_pool._pool]

    gb.gateways[0].stop()

    print(actual)
    assert expected == actual


def test_ws_signal_process():
    ws_main(1, 10)  # tested with 100


def test_ws_multi_processes():
    ws_main(32, 200)  # tested with 500


def test_ws_start_stop_and_error_handling():
    server = gb.start_gateway(WebsocketServer("127.0.0.1", 7985))

    # useless
    server.start()
    time.sleep(0.1)

    p = Process(target=ws_thread2, args=(WorkerController("0", gb.share), 0))
    p.start()

    time.sleep(0.5)  # got ConnectionClosedOK
    server.stop()
    time.sleep(0.1)


    client = gb.start_gateway(WebsocketClient("127.0.0.1", 7985))

    # useless
    client.start()
    time.sleep(0.1)
    # TODO
    time.sleep(0.5)
    client.stop()
