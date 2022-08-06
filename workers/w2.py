import time

from core.tools import WorkerController

import globals as gb


def run(worker: WorkerController):
    worker.init()

    gb.connect_server(("0.0.0.0", 7984))
    
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
    while True:
        # print("w2", gb.read(""))
        time.sleep(1)

    pass
