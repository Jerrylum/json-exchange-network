import time

from core.tools import WorkerController

import globals as gb


def run(worker: WorkerController):
    worker.init()
    
    # print("{} {} {} {} {}".format(
    #     isBtnPressing(RIGHT_U),
    #     isBtnJustPressed(RIGHT_U),
    #     isBtnJustReleased(RIGHT_U),
    #     getBtnDuration(RIGHT_U),
    #     getBtnCombo(RIGHT_U)
    # ))

    # print(gb.read('opcontrol.joystick'))

    # print(getAxis(LEFT_X))

    # print("{} {} {} {} {}".format(
    #     isBtnPressing("kb:space"),
    #     isBtnJustPressed("kb:space"),
    #     isBtnJustReleased("kb:space"),
    #     getBtnDuration("kb:space"),
    #     getBtnCombo("kb:space")
    # ))

    # time.sleep(5)
    # gen_output = gb.read("robot_gerenal.output")
    # gen_output["elevator"] = True
    # gb.write("robot_gerenal.output", gen_output)
    pass
