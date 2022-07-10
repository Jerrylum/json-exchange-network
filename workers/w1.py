import time

from consts import *
from core.opcontrol import *

import globals as gb


def run():

    g = False
    while True:
        # time.sleep(0.01)

        g = not g

        gb.write('robot.platform', g)
        gb.write('robot.run', str(g))


        time.sleep(0.1)
        # print("{} {} {} {} {}".format(
        #     isBtnPressing(RIGHT_U),
        #     isBtnJustPressed(RIGHT_U),
        #     isBtnJustReleased(RIGHT_U),
        #     getBtnDuration(RIGHT_U),
        #     getBtnCombo(RIGHT_U)
        # ))

        # print(gb.read('joystick.main'))

        # print(gb.read('joystick.main.axes'), end='                      \r')

        # gb.write('robot.main.update.time', time.time())
