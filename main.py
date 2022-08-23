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

import pathlib
import serial.tools.list_ports
from multiprocessing import Process
from types import ModuleType

import workers

from jen import *


if __name__ == '__main__':
    logger.info("List all available serial ports:")
    [print(p.serial_number, str(p) ) for p in list(serial.tools.list_ports.comports())]

    gb.init(pathlib.Path(__file__).parent / "initial.yml")
    gb.start_gateway(UDPBroadcast("255.255.255.255", 7986))
    # gb.start_gateway(UDPServer("127.0.0.1", 7984))  # use when needed
    # gb.start_gateway(WebsocketServer("127.0.0.1", 7985))  # use when needed

    processes: dict[str, Process] = {}
    for name in workers.__dict__:
        worker = workers.__dict__[name]
        if type(worker) is ModuleType and 'run' in worker.__dict__:
            p = Process(target=worker.run, args=(WorkerController(name, gb.share),))
            p.start()
            processes[name] = p
            # IMPORTANT: Slow it down to avoid process not started or hanged
            time.sleep(0.1)
    gb.mainloop(processes)

    logger.info("Program exit")
    os._exit(0)
