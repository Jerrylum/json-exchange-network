import sys
sys.path.insert(1, './')

from jen import *
from multiprocessing import Pool
import random
import pytest


def ws_sub(params: tuple[WorkerController, int] ):
    worker, i = params
    worker.init()

    client = gb.connect_websocket_server(("127.0.0.1", 7985))
    client.watching = set(["value_ws"])

    ans = None

    for _ in range(100):
        time.sleep(0.1)
        ans = gb.read("value_ws." + str(i))
        if ans is not None:
            break

    client.stop()

    return ans


def ws_main(pool_size: int, attempts: int):
    gb.gateways = []
    
    the_pool = Pool(pool_size)
    expected = list([i for i in range(attempts)])

    gb.create_websocket_server(("127.0.0.1", 7985))
    gb.write("value_ws", expected)
    
    with the_pool as p:
        actual = p.map(ws_sub, list([(WorkerController(str(i), { "conn": {} }), i) for i in range(attempts)]))

    [p.kill() for p in the_pool._pool]

    gb.gateways[0].stop()

    print(actual)
    assert expected == actual


def test_ws_signal_process():
    ws_main(1, 10)  # tested with 100


def test_ws_multi_processes():
    ws_main(32, 200)  # tested with 500
