import sys
sys.path.insert(1, './')

from jen import *
import jen.opcontrol
import random
import pytest


def get_signal(symbol: ButtonSymbol):
    return [
        isBtnPressing(symbol),
        isBtnJustPressed(symbol),
        isBtnJustReleased(symbol),
        getBtnDuration(symbol),
        getBtnCombo(symbol)
    ]


def test_get_channel_value():
    num = random.random()

    assert getChannelValue({"A": {"B": num}}, "A", "B") == num
    assert getChannelValue({"A": {"B": None}}, "A", "B") == None
    assert getChannelValue({"A": {}}, "A", "B") == 0

    assert getChannelValue({"A": {"B": num}}, "C", lambda data: data["A"]["B"]) == num
    assert getChannelValue({"A": {"B": None}}, "C", lambda data: data["A"]["B"]) == None
    assert getChannelValue({"A": {}}, "C", lambda data: data["A"]["B"]) == 0


def test_opcontrol_loop_spin_interval():
    gb.share = {"opcontrol": {"joystick": {"axes": {}, "btns": {}}, "keyboard": {"keys": {}}}}

    opcontrolLoop()
    test1 = jen.opcontrol.last_opcontrol_timestamp

    opcontrolLoop()
    assert test1 == jen.opcontrol.last_opcontrol_timestamp

    time.sleep(consts.OPCONTROL_SPIN_MINIMUM_INTERVAL)

    opcontrolLoop()
    assert test1 != jen.opcontrol.last_opcontrol_timestamp


def test_opcontrol_loop_prepare_symbol():
    gb.share = {"opcontrol": {"joystick": {"axes": {}, "btns": {}}, "keyboard": {"keys": {}}}}

    old_len = len(btn_table)

    opcontrolLoop("test")
    assert old_len + 1 == len(btn_table)

    gb.share = {"opcontrol": {"joystick": {"axes": {}, "btns": {}}, "keyboard": {"keys": {}}}}

    time.sleep(consts.OPCONTROL_SPIN_MINIMUM_INTERVAL)

    opcontrolLoop("kb:test")
    assert old_len + 2 == len(btn_table)

    time.sleep(consts.OPCONTROL_SPIN_MINIMUM_INTERVAL)

    gb.share = {"opcontrol": {"joystick": {"axes": {}, "btns": {}},
                              "keyboard": {"keys": {"test": False, "test2": False}}}}

    opcontrolLoop("kb:test")
    assert old_len + 3 == len(btn_table)


def test_opcontrol_functions():
    gb.share = {"opcontrol": {"joystick": {"axes": {}, "btns": {"test": False}}, "keyboard": {"keys": {}}}}
    assert get_signal("test") == [False, False, False, 0, 0]

    time.sleep(consts.OPCONTROL_SPIN_MINIMUM_INTERVAL)

    gb.share = {"opcontrol": {"joystick": {"axes": {}, "btns": {"test": False}}, "keyboard": {"keys": {}}}}
    assert get_signal("test") == [False, False, False, 0, 0]

    time.sleep(consts.OPCONTROL_SPIN_MINIMUM_INTERVAL)

    gb.share = {"opcontrol": {"joystick": {"axes": {}, "btns": {"test": True}}, "keyboard": {"keys": {}}}}
    assert get_signal("test")[:3] == [True, True, False]
    assert abs(get_signal("test")[3] - 0) < 0.01
    assert get_signal("test")[4] == 0

    time.sleep(1)

    gb.share = {"opcontrol": {"joystick": {"axes": {}, "btns": {"test": True}}, "keyboard": {"keys": {}}}}
    assert get_signal("test")[:3] == [True, False, False]
    assert abs(get_signal("test")[3] - 1) < 0.01
    assert get_signal("test")[4] == 0

    time.sleep(1)

    gb.share = {"opcontrol": {"joystick": {"axes": {}, "btns": {"test": True}}, "keyboard": {"keys": {}}}}
    assert get_signal("test")[:3] == [True, False, False]
    assert abs(get_signal("test")[3] - 2) < 0.01
    assert get_signal("test")[4] == 0

    time.sleep(1)

    gb.share = {"opcontrol": {"joystick": {"axes": {}, "btns": {"test": False}}, "keyboard": {"keys": {}}}}
    assert get_signal("test") == [False, False, True, 0, 0]

    time.sleep(consts.OPCONTROL_SPIN_MINIMUM_INTERVAL)

    gb.share = {"opcontrol": {"joystick": {"axes": {}, "btns": {"test": False}}, "keyboard": {"keys": {}}}}
    assert get_signal("test") == [False, False, False, 0, 0]

    for i in range(random.randint(30, 50)):

        time.sleep(consts.OPCONTROL_SPIN_MINIMUM_INTERVAL)

        gb.share = {"opcontrol": {"joystick": {"axes": {}, "btns": {"test": True}}, "keyboard": {"keys": {}}}}
        assert get_signal("test")[:3] == [True, True, False]
        assert get_signal("test")[4] == i

        time.sleep(consts.OPCONTROL_SPIN_MINIMUM_INTERVAL)

        gb.share = {"opcontrol": {"joystick": {"axes": {}, "btns": {"test": False}}, "keyboard": {"keys": {}}}}
        assert get_signal("test") == [False, False, True, 0, i]


def test_opcontrol_get_axis():
    gb.share = {"opcontrol": {"joystick": {"axes": {"test": 0.5}, "btns": {}}, "keyboard": {"keys": {}}}}
    assert getAxis("test") == 0.5
    assert getAxis("test2") == 0
