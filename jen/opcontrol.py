from typing import Union, Callable

import time

import jen.globals as gb
import jen.consts as consts


ButtonSymbol = Union[str, Callable[[any], bool]]


class BtnStatus:
    press = 0
    release = 0
    pressing = False
    combo = 0


btn_table: dict[ButtonSymbol, BtnStatus] = {s: BtnStatus() for s in [
    "LEFT_U","LEFT_R","LEFT_D","LEFT_L",
    "RIGHT_U","RIGHT_R","RIGHT_D","RIGHT_L",
    "LB","LT","RB","RT",
    "SELECT_BTN","START_BTN","MODE_BTN","LEFT_THUMB","RIGHT_THUMB"
]}

last_opcontrol_timestamp = 0

last_opcontrol_data = {}


def opcontrolLoop(prepareSymbol: ButtonSymbol = None):
    global last_opcontrol_timestamp, last_opcontrol_data

    if prepareSymbol is not None and prepareSymbol not in btn_table:
        btn_table[prepareSymbol] = BtnStatus()

    if time.perf_counter() - last_opcontrol_timestamp < consts.OPCONTROL_SPIN_MINIMUM_INTERVAL:
        return

    last_opcontrol_data = dict(gb.read("opcontrol"))  # IMPORTANT: use dict to make a shallow copy
    for key, _ in last_opcontrol_data["keyboard"]["keys"].items():
        if "kb:" + key not in btn_table:
            btn_table["kb:" + key] = BtnStatus()

    # around 0.05ms passed from the beginning of the method
    # we better set the last timestamp here instead of in the beginning of the method to maximize the time difference
    last_opcontrol_timestamp = now = time.perf_counter()

    for symbol, btn in btn_table.items():
        if type(symbol) is str and symbol.startswith("kb:"):
            now_pressing = getChannelValue(last_opcontrol_data["keyboard"], "keys", symbol[3:])
        else:
            now_pressing = getChannelValue(last_opcontrol_data["joystick"], "btns", symbol)

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

    return getChannelValue(last_opcontrol_data["joystick"], "axes", symbol)


def isBtnPressing(symbol: ButtonSymbol) -> bool:
    opcontrolLoop(symbol)

    return btn_table[symbol].pressing


def isBtnJustPressed(symbol: ButtonSymbol) -> bool:
    opcontrolLoop(symbol)

    return btn_table[symbol].press == last_opcontrol_timestamp


def isBtnJustReleased(symbol: ButtonSymbol) -> bool:
    opcontrolLoop(symbol)

    return btn_table[symbol].release == last_opcontrol_timestamp


def getBtnDuration(symbol: ButtonSymbol) -> float:
    opcontrolLoop(symbol)

    s = btn_table[symbol]
    return time.perf_counter() - s.press if s.pressing else 0


def getBtnCombo(symbol: ButtonSymbol) -> int:
    opcontrolLoop(symbol)

    return btn_table[symbol].combo
