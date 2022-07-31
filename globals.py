import threading
import uuid
import yaml
import os

from multiprocessing.managers import SyncManager, process
from multiprocessing.process import current_process

import consts

from core.tools import *

share: any = None
current_worker: WorkerController = None

def init(manager: SyncManager):
    global share
    share = {}

    initial_yml_file = os.path.dirname(os.path.realpath(__file__)) + "/initial.yml"
    with open(initial_yml_file, "r", encoding="utf-8") as stream:
        try:
            initial = yaml.safe_load(stream)
            for k in initial:
                anything = initial[k]
                share[k] = manager.dict(anything) if isinstance(anything, dict) else manager.list(anything)
        except:
            logger.critical("Failed to load initial.yml", exc_info=True)
            raise

    share['__diff__'] = manager.list([{"uuid": 0, "path": "ignored"}] * consts.DIFF_QUEUE_SIZE)
    share['__diff_condition__'] = manager.Condition()

    print('Share network initialized. ', manager.address, current_process().authkey)


def read(path: str):
    data = share
    try:
        if path == '':
            return {path: gb.read(path) for path in data if not path.startswith('_')}
        elif '.' not in path:
            return dict(data[path]) if hasattr(data[path], 'keys') else list(data[path])
        for key in path.split('.'):
            data = data[int(key)] if key.isdigit() else data[key]
        return data
    except:
        return None


def write(path: str, val: any):
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

    diff = {"uuid": uuid.uuid4().int >> (128 - 32), "path": path}

    if current_worker is not None:
        current_worker.serial_manager._sync_exact_match(diff, val)

    doRobot(share[nodes[0]], nodes[1:])

    if not path.startswith('_') and '._' not in path:
        # race condition might occur
        # XXX: ignored
        diffs: list = share['__diff__']
        diffs.append(diff)
        diffs.pop(0)
        condition: threading.Condition = share['__diff_condition__']
        with condition:
            condition.notify_all()

        if current_worker is not None:
            current_worker.serial_manager._sync_related(diff)
