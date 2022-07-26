import time

from consts import *
from core.opcontrol import *
from core.tools import *
from core.usb_serial import PortInfo

import globals as gb


def run(worker: WorkerController):
    worker.init()
    worker.use_clock(frequency=100)
    worker.serial_manager.whitelist.append(PortInfo(serial_number="5513132373735171A0B1"))
    worker.serial_manager.whitelist.append(PortInfo(serial_number="7513131383235170F071"))
    worker.serial_manager.start_listening()

    gen_output = gb.read("robot_gerenal.output")

    while True:
        if isBtnJustPressed(RIGHT_L):
            gen_output["BLDC"] = not gen_output["BLDC"]

        gen_output["elevator"] = isBtnPressing(RIGHT_U)
        gen_output["pusher"] = isBtnPressing(RIGHT_R)

        if isBtnJustPressed(RIGHT_D):
            gen_output["platform"] = not gen_output["platform"]

        gb.write("robot_gerenal.output", gen_output)

        # print("local", gen_output)
        # print("e", time.perf_counter())

        worker.spin()
