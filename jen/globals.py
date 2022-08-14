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


def read(path: str):
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
    return copy.deepcopy(read(path))


def write(path: str, val: any, early_sync=True, origin: Optional[DiffOrigin] = None):
    global share

    if "*" in path:
        raise KeyError("Wildcard not allowed in path")

    nodes = path.split(".")

    def doRobot(parent, cn):
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
        else:
            make_current = not current in parent  # or parent[current] is None

        if len(cn) == 1:
            ans = val
            if callable(val):
                parm = dict() if make_current else parent[current]
                val(parm)
                ans = parm
            parent[current] = ans
        else:
            if make_current:
                parent[current] = list() if cn[1].isdigit() else dict()
            parent[current] = doRobot(parent[current], cn[1:])
        return parent

    if read(path) == val:
        return

    diff = Diff.build(path, val)
    if early_sync:
        packet = DiffPacket().encode(path, val)
        [g._sync_exact_match(diff, packet, early=True) for g in early_gateways]

    if origin is not None:
        origin.ignored_diff_id.add(diff.uuid)

    if path == "":
        share = val
        logger.info("Global overwritten")
    else:
        doRobot(share, nodes)

    # XXX: TODO: race condition might occur
    diff_queue.append(diff)
    diff_queue.pop(0)

    with sync_condition:
        sync_condition.notify_all()


def init(initial_yml_file: Union[str, pathlib.Path]):
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


def mainloop(processes: dict[str, Process]):
    try:
        gb.write('process.main.pid', os.getpid())
        while True:
            gb.write('process.main.update', time.perf_counter())
            gb.write('process.subprocess', {
                name: {
                    'is_alive': processes[name].is_alive(),
                    'pid': processes[name].pid
                } for name in processes })
            time.sleep(0.2)
    except KeyboardInterrupt:
        logger.info("Main process keyboard interrupted")
    except BaseException:
        logger.exception("Exception in main process", exc_info=True)
    finally:
        logger.info("Killing workers")
        [p.kill() for p in processes.values()] 
