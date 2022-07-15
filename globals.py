from multiprocessing.managers import SyncManager, process
from multiprocessing.process import current_process
from typing import List

share = None


def init(manager: SyncManager, rootChannels: List[str]):
    global share
    share = {}

    for channel in rootChannels:
        share[channel] = manager.dict()

    share['__diff__'] = manager.list()

    print('Share network initialized. ', manager.address, current_process().authkey)


def read(path: str):
    def doRobot(parent, nodes):
        if len(nodes) == 0:
            return parent
        else:
            if hasattr(parent, '__getitem__'):  # is list or dict
                current = nodes[0]
                if hasattr(parent, 'append'):  # is list
                    if current.isdigit() and int(current) < len(parent):
                        return doRobot(parent[int(current)], nodes[1:])
                else:
                    if current in parent:
                        return doRobot(parent[current], nodes[1:])
        return None

    return doRobot(share, path.split('.'))

# def read(path: str):
#     data = share
#     try:
#         if path == '':
#            return data
#         for key in path.split('.'):
#             data = data[int(key)] if key.isdigit() else data[key]
#         return data
#     except:
#         return None


def write(path: str, val: any, remote_update=False):
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

    old_val = None if remote_update else read(path)

    doRobot(share[nodes[0]], nodes[1:])

    # if remote_update:
    #     pass
    # else:
    if old_val != read(path) and not path.startswith('_') and '._' not in path:
        share['__diff__'].append(path)
