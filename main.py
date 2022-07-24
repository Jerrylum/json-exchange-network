"""
DO NOT AUTO-FORMAT THIS FILE
DO NOT AUTO-FORMAT THIS FILE
DO NOT AUTO-FORMAT THIS FILE
"""

import sys

sys.path.insert(1, './') # XXX: to be able to import modules on project directory; this should be before other imports

import os
import time
from multiprocessing import Manager, Process
from types import ModuleType

import globals as gb
import workers

from core.tools import WorkerController


if __name__ == '__main__':
    # to allow tk window to be shown when the command is executed from terminal
    if 'DISPLAY' not in os.environ:
        os.environ['DISPLAY'] = ':0'

    try:
        gb.init(Manager(), ['device', 'opcontrol', 'process', 'robot'])

        processes: dict[str, Process] = {}

        for name in workers.__dict__:
            worker = workers.__dict__[name]
            if type(worker) is ModuleType and 'run' in worker.__dict__:
                p = Process(target=worker.run, args=(WorkerController(name, gb.share),))
                p.start()
                processes[name] = p

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
        print('Keyboard interrupt')

    [processes[name].kill() for name in processes]

    print('Program exit')

    exit()