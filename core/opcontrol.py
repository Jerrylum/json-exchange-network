from re import S
import time

import globals as gb
from consts import *


class BtnStatus:
    press = 0
    release = 0
    pressing = 0
    combo = 0


watchingBtnSymbol = [
    LEFT_U, LEFT_R, LEFT_D, LEFT_L,
    RIGHT_U, RIGHT_R, RIGHT_D, RIGHT_L,
    LB, LT, RB, RT,
    SELECT_BTN, START_BTN, MODE_BTN, LEFT_THUMB, RIGHT_THUMB
]
btnTable: dict[any, BtnStatus] = {s: BtnStatus() for s in watchingBtnSymbol}

lastOpcontrolTimestamp = 0

lastJoystickData = {}


def opcontrolLoop():
    global lastOpcontrolTimestamp, lastJoystickData

    now = time.time()
    if now - lastOpcontrolTimestamp < 0.002:
        return
    lastOpcontrolTimestamp = now

    lastJoystickData = gb.read('joystick.main')

    for symbol in watchingBtnSymbol:
        btn = btnTable[symbol]
        now_pressing = getChannelValue(lastJoystickData, 'btns', symbol)

        if btn.pressing != now_pressing:
            btn.pressing = now_pressing
            if btn.pressing:
                btn.combo += now - btn.press < 0.4
                btn.press = now
            else:
                btn.release = now

        if now - btn.press >= 0.4 and not now_pressing:
            btn.combo = 0


def getChannelValue(data, typename, symbol):
    try:
        if type(symbol) == str:
            rtn = data[typename][symbol]
        else:
            rtn = symbol(data)
        return rtn
    except:
        pass
    return 0


def isBtnPressing(symbol):
    opcontrolLoop()

    return btnTable[symbol].pressing


def isBtnJustPressed(symbol):
    opcontrolLoop()

    return btnTable[symbol].press == lastOpcontrolTimestamp


def isBtnJustReleased(symbol):
    opcontrolLoop()

    return btnTable[symbol].release == lastOpcontrolTimestamp


def getBtnDuration(symbol):
    opcontrolLoop()

    s = btnTable[symbol]
    return time.time() - s.press if s.pressing else 0


def getBtnCombo(symbol):
    opcontrolLoop()

    return btnTable[symbol].combo
