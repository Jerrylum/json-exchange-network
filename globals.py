import threading
from typing import Optional
import yaml
import os
import copy
import threading
import time
import uuid

import consts

from core.protocol import *
from core.tools import *
from core.gateway import *
from core.udp import *

diff_queue = [Diff.placeholder()] * consts.DIFF_QUEUE_SIZE
sync_condition = threading.Condition()

share: any = None
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


def read_copy(path: str):
    return copy.deepcopy(read(path))


def write(path: str, val: any, early_sync=True, origin: Optional[DiffOrigin]=None):
    global share

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
        packet = DataPatchPacket().encode(path, val)

        if len(early_gateways) == 1:
            print("e", time.perf_counter())
        [g._sync_exact_match(diff, packet, early=True) for g in early_gateways]

    if origin is not None:
        origin.ignored_diff_id.add(diff.uuid)
    
    if path == "":
        share = val
        print("global overwrite")
    else:
        doRobot(share, nodes)

    # XXX: TODO: race condition might occur
    diff_queue.append(diff)
    diff_queue.pop(0)

    with sync_condition:
        sync_condition.notify_all()


def init():
    global share

    initial_yml_file = os.path.dirname(os.path.realpath(__file__)) + "/initial.yml"
    with open(initial_yml_file, "r", encoding="utf-8") as stream:
        try:
            share = yaml.safe_load(stream)
        except:
            logger.critical("Failed to load initial.yml", exc_info=True)
            raise


    server = UDPServer()
    server.start_listening()
    gateways.append(server)


def connect_server(addr: Address):
    client = UDPClient(addr)
    client.start()
    gateways.append(client)
