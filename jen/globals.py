import copy
import threading
import pathlib
import os
import yaml
from multiprocessing import Process

from .gateway import *


diff_queue = [Diff.placeholder()] * consts.DIFF_QUEUE_SIZE
sync_condition = threading.Condition()

share: any = {"conn": {}}
current_worker: WorkerController = None
gateways: list[Gateway] = []
early_gateways: list[Gateway] = []


def read(path: str) -> Union[any, None]:
    """
    Read a value from the cache. Return None if the path does not exist.

    Do not modify the returned value as it is a reference to the value in the cache.

    :param path: The path to the value.
    :return: The value.
    """
    data = share
    try:
        if path == "":
            return {path: gb.read(path) for path in data if not path.startswith("_")}
        for key in path.split("."):
            data = data[int(key)] if key.isdigit() else data[key]
        return data
    except:
        return None


def clone(path: str):
    """
    Clone a value from the cache. Return None if the path does not exist.

    :param path: The path to the value.
    :return: The value.
    """
    return copy.deepcopy(read(path))


def _write(parent, cn, path: str, val: any):
    """
    Write a value to an object or array. Create the path if it does not exist.

    :param parent: The parent object.
    :param cn: The path separated by ".".
    :param path: The path to the value.
    :param val: The value.
    """
    if not hasattr(parent, "__getitem__"):
        raise KeyError('Trying to subscribe but parent is not a list or dict. On path "%s" via "%s"' % (
            path, ".".join(cn)))

    current = cn[0]
    make_current = False
    if hasattr(parent, "append"):  # is list
        if not current.isdigit():
            raise KeyError('The parent is a list but key is not a number. On path "%s" via "%s"' % (
                path, ".".join(cn)))
        current = int(current)
        if not current < len(parent):
            parent.extend([None] * (current - len(parent) + 1))
            make_current = True
    else:  # TODO: raise KeyError if current is a number but parent is a dict
        make_current = not current in parent  # or parent[current] is None

    if len(cn) == 1:
        ans = val
        if callable(val):
            parm = dict() if make_current else parent[current]
            val(parm)  # TODO: remove this line
            ans = parm
        parent[current] = ans
    else:
        if make_current:
            parent[current] = list() if cn[1].isdigit() else dict()
        parent[current] = _write(parent[current], cn[1:], path, val)
    return parent


def write(path: str, val: any, early_sync=True, origin: Optional[DiffOrigin] = None):
    """
    Write a value to the cache. Create the path if it does not exist. For example: write("a.b.c", 1) will create at
    most 3 objects in the cache: a, b, and c. If the path contains a number, it will be treated as a list index.

    Do not reuse the passed value `val` as it is a reference to the value in the cache. Create a copy before passing
    it to this function. For example: write("a.b.c", copy.deepcopy(...))

    :param path: The path to the value.
    :param val: The value.
    :param early_sync: Whether to sync the value to early gateways immediately.
    :param origin: The origin (gateway or connection) of the value.
    :raise ValueError: If the path is invalid.
    """

    global share

    if "*" in path:
        raise KeyError("Wildcard not allowed in path")

    nodes = path.split(".")

    if read(path) == val:
        return

    diff = Diff.build(path, val)
    if early_sync:
        [g._sync_exact_match(diff, g.diff_packet_type().encode_diff(diff), early=True) for g in early_gateways]

    if origin is not None:
        origin.ignored_diff_id.add(diff.diff_id)

    if path == "":
        share = val
        logger.info("Global overwritten")
    else:
        _write(share, nodes, path, val)

    # XXX: FIXING: race condition might occur
    with sync_condition:
        diff_queue.append(diff)
        diff_queue.pop(0)
        sync_condition.notify_all()


def init(initial_yml_file: Union[str, pathlib.Path]):
    """
    Initialize the cache.

    :param initial_yml_file: The path to the initial yml file.
    """
    global share

    with open(str(initial_yml_file), "r", encoding="utf-8") as stream:
        try:
            share = yaml.safe_load(stream)
        except:
            logger.critical("Failed to load initial.yml", exc_info=True)
            raise


def create_server(addr: Address):
    from jen.udp import UDPServer

    server = UDPServer(addr)
    server.start_listening()
    gateways.append(server)
    return server


def connect_server(addr: Address):
    from jen.udp import UDPClient

    client = UDPClient(addr)
    client.start()
    gateways.append(client)
    return client


def create_websocket_server(addr: Address):
    from jen.ws import WebsocketServer

    server = WebsocketServer(addr)
    server.start_listening()
    gateways.append(server)
    return server


def connect_websocket_server(addr: Address):
    from jen.ws import WebsocketClient

    client = WebsocketClient(addr)
    client.start()
    gateways.append(client)
    return client


def join_broadcast(addr: Address, listen= True):
    from jen.udpb import UDPBroadcast

    client = UDPBroadcast(addr, listen)
    client.start()
    gateways.append(client)
    return client


def mainloop(processes: dict[str, Process]):
    """
    The main loop of the program. This function should be called by the main process.

    :param processes: The processes to be monitored.
    """
    try:
        gb.write('process.main.pid', os.getpid())
        while gb.read("stop") is False:
            gb.write('process.main.update', time.perf_counter())
            gb.write('process.subprocess', {
                name: {
                    'is_alive': processes[name].is_alive(),
                    'pid': processes[name].pid
                } for name in processes})
            time.sleep(0.2)
    except KeyboardInterrupt:
        logger.info("Main process keyboard interrupted")
    except BaseException:
        logger.exception("Exception in main process", exc_info=True)
    finally:
        logger.info("Killing workers")
        [p.kill() for p in processes.values()]
