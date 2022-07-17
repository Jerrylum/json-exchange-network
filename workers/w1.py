import time

from consts import *
from core.opcontrol import *
from core.tools import *

import globals as gb


def run(share):
    gb.share = share

    time.sleep(1)

    c = Clock(frequency = 100)

    g = False
    while True:
        c.spin()

        g = not g

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

        # print(gb.read('joystick.main'))

        # print(gb.read('joystick.main.axes'), end='                      \r')

        # gb.write('robot.main.update.time', time.perf_counter())
