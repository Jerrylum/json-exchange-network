import time

from consts import *
from core.opcontrol import *
from core.tools import *
from core.usb_serial import PortInfo

import globals as gb


def run(worker: WorkerController):
    worker.init()
    worker.use_clock(frequency=100)
    # worker.serial_manager.whitelist.append(PortInfo(serial_number="5513132373735171A0B1"))
    # worker.serial_manager.whitelist.append(PortInfo(serial_number="7513131383235170F071"))
    # worker.serial_manager.start_listening()

    gen_output = gb.read("rg.o")
    shooter_output = gb.read("rs.o")

    # import msgpack
    # print(msgpack.packb(dict(gb.read("rg"))))
    # print(gb.read("rh.0"))
    # print(gb.read(""))

    while True:
        w = time.perf_counter()
        gen_output[0] = gen_output[0] + 1
        gb.write("rg.o", gen_output)
        e = time.perf_counter()
        logger.debug("%s: %f" % ("Send", w))
        logger.debug("%s: %f" % ("Receive", e))

        # if isBtnJustPressed(RIGHT_L):
        #     gen_output[0] = not gen_output[0]

        # gen_output[1] = isBtnPressing(RIGHT_U)
        # gen_output[2] = isBtnPressing(RIGHT_R)

        # if isBtnJustPressed(RIGHT_D):
        #     gen_output[3] = not gen_output[3]

        # gb.write("rg.o", gen_output)

        # shooter_output[0] = int(getAxis(LEFT_X) * 8192 * 19 * (45 / 360) * 7)
        # shooter_output[1] = int(-getAxis(LEFT_Y) * 8192 * 19 * (150 / 360))

        # gb.write("rs.o", shooter_output)

        # # print("local", gen_output)
        # # print("e", time.perf_counter())
        # # print("feedback", gb.read("rg.f"))

        worker.spin()
