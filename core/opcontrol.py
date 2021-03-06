from typing import Union, Callable

import time

import globals as gb
from consts import *


ButtonSymbol = Union[str, Callable[[any], bool]]


class BtnStatus:
    press = 0
    release = 0
    pressing = False
    combo = 0


btnTable: dict[ButtonSymbol, BtnStatus] = {s: BtnStatus() for s in [
    LEFT_U, LEFT_R, LEFT_D, LEFT_L,
    RIGHT_U, RIGHT_R, RIGHT_D, RIGHT_L,
    LB, LT, RB, RT,
    SELECT_BTN, START_BTN, MODE_BTN, LEFT_THUMB, RIGHT_THUMB
]}

lastOpcontrolTimestamp = 0

lastOpcontrolData = {}


def opcontrolLoop(prepareSymbol: ButtonSymbol = None):
    global lastOpcontrolTimestamp, lastOpcontrolData

    if prepareSymbol is not None and prepareSymbol not in btnTable:
        btnTable[prepareSymbol] = BtnStatus()

    if time.perf_counter() - lastOpcontrolTimestamp < 0.003:
        return

    lastOpcontrolData = dict(gb.read('opcontrol'))  # IMPORTANT: use dict to make a shallow copy

    for key, _ in lastOpcontrolData['keyboard']['keys'].items():
        if 'kb:' + key not in btnTable:
            btnTable['kb:' + key] = BtnStatus()

    # around 1.1ms passed from the beginning of the method, that's why we need to set the last timestamp here instead
    # of in the beginning of the method to maximize the time difference
    lastOpcontrolTimestamp = now = time.perf_counter()

    for symbol, btn in btnTable.items():
        if type(symbol) is str and symbol.startswith('kb:'):
            now_pressing = getChannelValue(lastOpcontrolData['keyboard'], 'keys', symbol[3:])
        else:
            now_pressing = getChannelValue(lastOpcontrolData['joystick'], 'btns', symbol)

        if btn.pressing != now_pressing:
            btn.pressing = now_pressing
            if btn.pressing:
                btn.combo += now - btn.press < 0.4
                btn.press = now
            else:
                btn.release = now

        if now - btn.press >= 0.4 and not now_pressing:
            btn.combo = 0


def getChannelValue(data: any, typename: str, symbol: ButtonSymbol):
    try:
        if type(symbol) == str:
            rtn = data[typename][symbol]
        else:
            rtn = symbol(data)
        return rtn
    except:
        pass
    return 0


def getAxis(symbol: ButtonSymbol) -> float:
    opcontrolLoop(symbol)

    return getChannelValue(lastOpcontrolData['joystick'], 'axes', symbol)


def isBtnPressing(symbol: ButtonSymbol) -> bool:
    opcontrolLoop(symbol)

    return btnTable[symbol].pressing


def isBtnJustPressed(symbol: ButtonSymbol) -> bool:
    opcontrolLoop(symbol)

    return btnTable[symbol].press == lastOpcontrolTimestamp


def isBtnJustReleased(symbol: ButtonSymbol) -> bool:
    opcontrolLoop(symbol)

    return btnTable[symbol].release == lastOpcontrolTimestamp


def getBtnDuration(symbol: ButtonSymbol) -> float:
    opcontrolLoop(symbol)

    s = btnTable[symbol]
    return time.perf_counter() - s.press if s.pressing else 0


def getBtnCombo(symbol: ButtonSymbol) -> int:
    opcontrolLoop(symbol)

    return btnTable[symbol].combo
