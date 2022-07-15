from math import e
import time

from lib import japi

import globals as gb


def run(share):
    gb.share = share

    print("Joystick worker started")

    gb.write('opcontrol.joystick', {'available': False, 'update': 0, 'axes': {}, 'btns': {}})

    while True:
        paths = japi.getAvailableJoysticks()

        if len(paths) == 0:
            print("No joystick found, waiting for one. At: " + str(time.perf_counter()))
            time.sleep(1)
            continue

        if len(paths) > 1:
            print("More than one joystick found, using first one")

        joystick = None

        try:
            joystick = japi.Joystick(paths[0])

            print("Joystick found, starting to read")

            while True:
                joystick.read()  # ignore returned result

                gb.write('opcontrol.joystick', {
                    'available': True,
                    'update': time.perf_counter(),
                    'axes': joystick.axis_states,
                    'btns': joystick.button_states
                })
        except:
            print("Joystick error, disconnecting")

            if joystick is not None:
                joystick.close()

            gb.write('opcontrol.joystick.available', False)
