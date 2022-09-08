#!/bin/python3

"""
DO NOT AUTO-FORMAT THIS FILE
DO NOT AUTO-FORMAT THIS FILE
DO NOT AUTO-FORMAT THIS FILE
"""

import pathlib
import serial.tools.list_ports
from multiprocessing import Process

import workers

from jen import *


if __name__ == '__main__':
    logger.info("List all available serial ports:")
    [print("%s - vid:%s pid:%s sno:%s (%s)" % (p.device, p.vid, p.pid, p.serial_number, p.description)) for p in list(serial.tools.list_ports.comports())]

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
