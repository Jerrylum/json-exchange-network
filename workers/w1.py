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

    gen_output = gb.read("rg.o")
    shooter_output = gb.read("rs.o")

    while True:
        if isBtnJustPressed(RIGHT_L):
            gen_output["BLDC"] = not gen_output["BLDC"]

        gen_output["e"] = isBtnPressing(RIGHT_U)
        gen_output["pu"] = isBtnPressing(RIGHT_R)

        if isBtnJustPressed(RIGHT_D):
            gen_output["pl"] = not gen_output["pl"]

        gb.write("rg.o", gen_output)

        shooter_output["sx"]["pos"] = int(getAxis(LEFT_X) * 8192 * 19 * (45 / 360) * 7)
        shooter_output["sy"]["pos"] = int(-getAxis(LEFT_Y) * 8192 * 19 * (150 / 360))

        gb.write("rs.o", shooter_output)

        # print("local", gen_output)
        # print("e", time.perf_counter())

        worker.spin()
