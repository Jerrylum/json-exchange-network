"""
DO NOT AUTO-FORMAT THIS FILE
DO NOT AUTO-FORMAT THIS FILE
DO NOT AUTO-FORMAT THIS FILE
"""

import sys
sys.path.insert(1, './') # XXX: to be able to import modules on project directory; this should be before other imports

import os
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'
# to allow tk window to be shown when the command is executed from terminal
if 'DISPLAY' not in os.environ:
    os.environ['DISPLAY'] = ':0'

import time
import pathlib
import serial.tools.list_ports
from multiprocessing import Process
from types import ModuleType

import workers

from jen import *


if __name__ == '__main__':
    try:
        logger.info("List all available serial ports:")
        [print(p.serial_number, str(p) ) for p in list(serial.tools.list_ports.comports())]

        processes: dict[str, Process] = {}

        gb.init(str(pathlib.Path(__file__).parent.absolute()) + "/initial.yml")
        gb.create_server(("127.0.0.1", 7984))

        for name in workers.__dict__:
            worker = workers.__dict__[name]
            if type(worker) is ModuleType and 'run' in worker.__dict__:
                p = Process(target=worker.run, args=(WorkerController(name, gb.share),))
                p.start()
                processes[name] = p
                # IMPORTANT: Slow it down to avoid process not started or hanged
                time.sleep(0.1)

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

        logger.info("Program exit")

        os._exit(0)
