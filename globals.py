import uuid

from multiprocessing.managers import SyncManager, process
from multiprocessing.process import current_process
from typing import List

import consts

from core.tools import WorkerController

share: any = None
current_worker: WorkerController = None

def init(manager: SyncManager, rootChannels: List[str]):
    global share
    share = {}

    for channel in rootChannels:
        share[channel] = manager.dict()

    share['__diff__'] = manager.list([{"uuid": 0, "path": "ignored"}] * consts.DIFF_QUEUE_SIZE)

    print('Share network initialized. ', manager.address, current_process().authkey)


def read(path: str):
    data = share
    try:
        for key in path.split('.'):
            data = data[int(key)] if key.isdigit() else data[key]
        return data
    except:
        return None


def write(path: str, val: any, remote_update=False, unsafe=False):
    nodes = path.split('.')
    if len(nodes) <= 1:
        # Changing all channels is not allowed
        raise KeyError('Changing the root key is not allowed')

    def doRobot(parent, cn):
        if not hasattr(parent, '__getitem__'):
            raise KeyError('Trying to subscribe but parent is not a list or dict. On path "%s" via "%s"' % (
                path, '.'.join(cn)))

        current = cn[0]
        make_current = False
        if hasattr(parent, 'append'):  # is list
            if not current.isdigit():
                raise KeyError('The parent is a list but key is not a number. On path "%s" via "%s"' % (
                    path, '.'.join(cn)))
            current = int(current)
            if not current < len(parent):
                parent.extend([None] * (current - len(parent) + 1))
                make_current = True
        else:
            make_current = not current in parent # or parent[current] is None

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

    diff = {"uuid": uuid.uuid4().int >> (128 - 32), "path": path}

    if unsafe and current_worker is not None:
        current_worker.serial_manager._sync_exact_match(diff, val)

    doRobot(share[nodes[0]], nodes[1:])

    if not path.startswith('_') and '._' not in path:
        # race condition might occur
        # XXX: ignored
        share['__diff__'].append(diff)
        share['__diff__'].pop(0)

        if unsafe and current_worker is not None:
            current_worker.serial_manager._sync_related(diff)
