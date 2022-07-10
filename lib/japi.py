# BSD 3-Clause License
# Copyright (c) 2019, Regents of the CMAss Robotics Team
# All rights reserved.

import os
import struct
import array
from fcntl import ioctl


# These constants were borrowed from linux/input.h
AXIS_NAMES = {
    0x00: 'x',
    0x01: 'y',
    0x02: 'z',
    0x03: 'rx',
    0x04: 'ry',
    0x05: 'rz',
    0x06: 'trottle',
    0x07: 'rudder',
    0x08: 'wheel',
    0x09: 'gas',
    0x0a: 'brake',
    0x10: 'hat0x',
    0x11: 'hat0y',
    0x12: 'hat1x',
    0x13: 'hat1y',
    0x14: 'hat2x',
    0x15: 'hat2y',
    0x16: 'hat3x',
    0x17: 'hat3y',
    0x18: 'pressure',
    0x19: 'distance',
    0x1a: 'tilt_x',
    0x1b: 'tilt_y',
    0x1c: 'tool_width',
    0x20: 'volume',
    0x28: 'misc'
}

BUTTON_NAMES = {
    0x120: 'trigger',
    0x121: 'thumb',
    0x122: 'thumb2',
    0x123: 'top',
    0x124: 'top2',
    0x125: 'pinkie',
    0x126: 'base',
    0x127: 'base2',
    0x128: 'base3',
    0x129: 'base4',
    0x12a: 'base5',
    0x12b: 'base6',
    0x12f: 'dead',
    0x130: 'a',
    0x131: 'b',
    0x132: 'c',
    0x133: 'x',
    0x134: 'y',
    0x135: 'z',
    0x136: 'tl',
    0x137: 'tr',
    0x138: 'tl2',
    0x139: 'tr2',
    0x13a: 'select',
    0x13b: 'start',
    0x13c: 'mode',
    0x13d: 'thumbl',
    0x13e: 'thumbr',

    0x220: 'dpad_up',
    0x221: 'dpad_down',
    0x222: 'dpad_left',
    0x223: 'dpad_right',

    # XBox 360 controller uses these codes.
    0x2c0: 'dpad_left',
    0x2c1: 'dpad_right',
    0x2c2: 'dpad_up',
    0x2c3: 'dpad_down'
}


def getAvailableJoysticks():
    """
    Return: a list of joystick's name
    """
    rtn_list = []
    try:
        for fn in os.listdir('/dev/input/by-id'):
            # need: usb-Microsoft_Controller_7EED867F0E86-joystick
            # not:  usb-Microsoft_Controller_7EED867F0E86-event-joystick
            if fn.endswith('-joystick') and not fn.endswith('-event-joystick'):
                rtn_list.append(fn)
    except:
        pass
    return rtn_list


class Joystick:
    # The hardware link, like: /dev/input/by-id/{id}
    device_path = None

    # The joystick name + symbol code, listed on /dev/input/by-id/
    uuid = None

    # It can be None if joystick init with device_path or name,
    # the position in the input list, it update once only in the __init__
    idx = None

    # We'll store the states here.
    axis_states = {}
    button_states = {}

    axis_map = []
    button_map = []

    # The number of axes and buttons.
    num_axes = None
    num_buttons = None

    # The 'file' object, open in __init__
    _jsdev = None

    # The joystick name(up to 64 bytes) provided by the joystick
    _name = None

    def __init__(self, *args):
        """
        Args:
        symbol -- the index of the joysticks list or
                  a full device path or
                  a joystick name
        """
        symbol = args[0]

        if type(symbol) == int:
            self.idx = symbol
            self.uuid = getAvailableJoysticks()[self.idx]
            self.device_path = '/dev/input/by-id/' + self.uuid
        elif type(symbol) == str:
            if '/' in symbol:
                self.device_path = symbol
                self.uuid = self.device_path.split('/')[-1]
            else:
                self.uuid = symbol
                self.device_path = '/dev/input/by-id/' + self.uuid
        else:
            raise TypeError('not support symbol type for init joystick')

        _jsdev = open(self.device_path, 'rb')
        self._jsdev = _jsdev

        # Get the device name.
        #buf = bytearray(63)
        buf = array.array('b', [0] * 64)
        ioctl(_jsdev, 0x80006a13 + (0x10000 * len(buf)), buf)  # JSIOCGNAME(len)
        self._name = buf.tobytes().decode()

        # Get number of axes and buttons.
        buf = array.array('B', [0])
        ioctl(_jsdev, 0x80016a11, buf)  # JSIOCGAXES
        self.num_axes = buf[0]

        buf = array.array('B', [0])
        ioctl(_jsdev, 0x80016a12, buf)  # JSIOCGBUTTONS
        self.num_buttons = buf[0]

        # Get the axis map.
        buf = array.array('B', [0] * 0x40)
        ioctl(_jsdev, 0x80406a32, buf)  # JSIOCGAXMAP

        for axis in buf[:self.num_axes]:
            axis_name = AXIS_NAMES.get(axis, 'unknown(0x%02x)' % axis)
            self.axis_map.append(axis_name)
            self.axis_states[axis_name] = 0.0

        # Get the button map.
        buf = array.array('H', [0] * 200)
        ioctl(_jsdev, 0x80406a34, buf)  # JSIOCGBTNMAP

        for btn in buf[:self.num_buttons]:
            btn_name = BUTTON_NAMES.get(btn, 'unknown(0x%03x)' % btn)
            self.button_map.append(btn_name)
            self.button_states[btn_name] = 0

    def read(self):
        """
        wait until receive new joystick signal
        Return: A list of JoystickEvent
        """
        evbuf = self._jsdev.read(8)
        updated = []
        if evbuf:
            time, value, type, number = struct.unpack('IhBB', evbuf)

            if type & 0x80:
                updated.append(JoystickEvent('initial', None, None))

            if type & 0x01:
                button = self.button_map[number]
                if button:
                    self.button_states[button] = value
                    updated.append(JoystickEvent('button', button, value))

            if type & 0x02:
                axis = self.axis_map[number]
                if axis:
                    fvalue = value / 32767.0
                    self.axis_states[axis] = fvalue
                    updated.append(JoystickEvent('axis', axis, fvalue))
        return updated

    def close(self):
        """
        Flush and close the Joystick IO object.
        Return: True if the IO object is closed successfully
        """
        try:
            self._jsdev.close()
            self._jsdev = None
        except:
            pass
        return self.is_open()

    def is_open(self):
        """
        Return: True if the IO object is closed
        """
        return self._jsdev is not None


class JoystickEvent:
    def __init__(self, t, n, v):
        """
        Args:
        t -- the type of the event, it must be 'initial', 'button' or 'axis'
        n -- the channel name
        v -- the new value of the channel
        """
        self.type = t
        self.name = n  # it can be None if it is a initial event
        self.value = v  # it can be None if it is a initial event

    def __str__(self):
        return str(self.__dict__)

    def __repr__(self):
        return '%s.%s(%s, %s, %s)' % (
            self.__module__,
            self.__class__.__name__,
            self.type,
            self.name,
            self.value)