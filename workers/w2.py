from jen import *


def run(worker: WorkerController):
    worker.init()

    gb.connect_server(("127.0.0.1", 7984))
    
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
        time.sleep(1)

    pass
