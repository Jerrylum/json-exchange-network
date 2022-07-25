import time

from consts import *
from core.opcontrol import *
from core.tools import *
from core.usb_serial import PortInfo

import globals as gb


def run(worker: WorkerController):
    worker.init()
    worker.use_clock(frequency = 100)
    worker.serial_manager.whitelist.append(PortInfo(serial_number="5513132373735171A0B1"))
    worker.serial_manager.whitelist.append(PortInfo(serial_number="7513131383235170F071"))
    # worker.serial_manager.async_spin()

    time.sleep(1)

    gen_output = gb.read("robot_gerenal.output")

    g = False
    while True:
        g = not g

        if isBtnJustPressed(RIGHT_L):
            gen_output["BLDC"] = not gen_output["BLDC"]

        gen_output["elevator"] = isBtnPressing(RIGHT_U)
        gen_output["pusher"] = isBtnPressing(RIGHT_R)

        if isBtnJustPressed(RIGHT_D):
            gen_output["platform"] = not gen_output["platform"]

        gb.write("robot_gerenal.output", gen_output)

        # print("FFFFFFFFFF", gen_output)

        # print("AH", time.perf_counter())
        # for i in range(1):
        #     gb.read('robot.platform')
        # print("AHE", time.perf_counter())

        # print("e", time.perf_counter())
        # gb.write('robot.platform', g, unsafe=True)
        # gb.write('robot.platform', g)
        # gb.write('robot.run', str(g))

        # print("{} {} {} {} {}".format(
        #     isBtnPressing(RIGHT_U),
        #     isBtnJustPressed(RIGHT_U),
        #     isBtnJustReleased(RIGHT_U),
        #     getBtnDuration(RIGHT_U),
        #     getBtnCombo(RIGHT_U)
        # ))

        # print(gb.read('opcontrol.joystick'))

        # print(getAxis(LEFT_X))

        # print(gb.read('opcontrol.keyboard.keys'))

        # print("{} {} {} {} {}".format(
        #     isBtnPressing("kb:space"),
        #     isBtnJustPressed("kb:space"),
        #     isBtnJustReleased("kb:space"),
        #     getBtnDuration("kb:space"),
        #     getBtnCombo("kb:space")
        # ))

        # print(gb.read('joystick.main.axes'), end='                      \r')

        worker.spin()
