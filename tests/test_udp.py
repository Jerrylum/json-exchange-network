import sys
sys.path.insert(1, './')

from jen import *
from multiprocessing import Pool, Process
import random
import pytest


def udp_thread(params: tuple[WorkerController, int] ):
    worker, i = params
    worker.init()

    client = UDPClient("127.0.0.1", 7984)
    client.watching = set(["value_udp"])
    gb.start_gateway(client)

    ans = None

    for _ in range(100):
        # wait for the server to send the diff, 10 seconds maximum
        # the connection might reset several times since the server is not reliable
        # data from various connections are merged together sometimes
        # however, the client should be able to recover from the error
        time.sleep(0.1)
        ans = gb.read("value_udp." + str(i))
        if ans is not None:
            break

    gb.write("conn." + str(client.conn_id), None)
    gb.write("last", client.conn_id)
    time.sleep(0.1)
    client.stop()

    return ans


def udp_thread2(worker: WorkerController, i: list):
    worker.init()

    server = gb.start_gateway(UDPServer("127.0.0.1", 7984))
    time.sleep(1)
    gb.write("value_udp2", i)
    time.sleep(0.1)
    server.stop()


def udp_main(pool_size: int, attempts: int):
    gb.gateways = []
    
    the_pool = Pool(pool_size)
    expected = list([random.randint(0, 1000) for _ in range(attempts)])

    gb.start_gateway(UDPServer("127.0.0.1", 7984))
    gb.write("value_udp", expected)
    
    with the_pool as p:
        actual = p.map(udp_thread, list([(WorkerController(str(i), { "conn": {} }), i) for i in range(attempts)]))

    [p.kill() for p in the_pool._pool]

    logger.setLevel(logging.CRITICAL)  # disable logging to prevent logging error

    gb.gateways[0].stop()

    print(actual)
    assert expected == actual


def test_udp_signal_process():
    udp_main(1, 10)  # tested with 100


def test_udp_multi_processes():
    udp_main(32, 200)  # tested with 500


def test_udp_start_stop_and_error_handling():
    server = gb.start_gateway(UDPServer("127.0.0.1", 7984))

    # useless
    server.start()
    time.sleep(0.1)
    so = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    so.sendto(b'\x00', ("127.0.0.1", 7984))
    time.sleep(0.1)
    server.stop()
    time.sleep(0.1)

    old_val = consts.CONNECTION_TIMEOUT
    consts.CONNECTION_TIMEOUT = 0.5
    client = gb.start_gateway(UDPClient("127.0.0.1", 7984))

    # useless
    client.start()
    time.sleep(0.1)
    try:
        client.s.shutdown(socket.SHUT_RDWR)
    except:
        pass
    time.sleep(0.5)
    client.stop()
    consts.CONNECTION_TIMEOUT = old_val


def test_udp_client_process():
    expected = list([random.randint(0, 1000) for _ in range(100)])

    client = UDPClient("127.0.0.1", 7984)
    client.watching = set(["value_udp2"])
    gb.start_gateway(client)

    p = Process(target=udp_thread2, args=(WorkerController("0", gb.share), expected))
    p.start()

    actual = None
    for _ in range(100):
        # wait for the server to send the diff, 10 seconds maximum
        # the connection might reset several times since the server is not reliable
        # data from various connections are merged together sometimes
        # however, the client should be able to recover from the error
        time.sleep(0.1)
        actual = gb.read("value_udp2")
        if actual is not None:
            break

    p.kill()

    logger.setLevel(logging.CRITICAL)  # disable logging to prevent logging error

    client.stop()

    print(actual)
    assert expected == actual
