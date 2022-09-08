"""
DO NOT AUTO-FORMAT THIS FILE
DO NOT AUTO-FORMAT THIS FILE
DO NOT AUTO-FORMAT THIS FILE
"""

import os
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'

import platform
import pygame

from jen import *


def axis(val: float):
    if abs(val) < consts.JOYSTICK_AXIS_THRESHOLD:
        val = 0
    return val


def run(worker: WorkerController):
    worker.init()

    client = gb.start_gateway(UDPBroadcast("255.255.255.255", 7986, False))
    # client = gb.start_gateway(UDPClient("127.0.0.1", 7984))
    # client.watching = set(["process.main.update", "opcontrol.joystick", "opcontrol.joystick.*"])
    gb.early_gateways.append(client)

    pygame.init()

    while True:
        try:
            while pygame.joystick.get_count() == 0:
                pygame.event.pump()

                gb.write("opcontrol.joystick.available", False)

                if consts.JOYSTICK_DISCONNECTION_SAFETY:
                    gb.write("opcontrol.joystick.axes", {})
                    gb.write("opcontrol.joystick.btns", {})

                logger.info("Waiting for joystick...")

                time.sleep(1)

            joystick = pygame.joystick.Joystick(0)
            name = joystick.get_name()
            is_xbox = "box" in name or "microsoft" in name
            is_win = platform.system() == "Windows"

            if pygame.joystick.get_count() > 1:
                logger.warning("More than one joystick connected, using the first one")

            logger.info("Listening joystick: %s - %s" % (joystick.get_guid(), name))

            while pygame.joystick.get_count() != 0:
                pygame.event.wait(consts.JOYSTICK_UPDATE_MAXIMUM_INTERVAL * 1000)
                pygame.event.pump()

                axes = [joystick.get_axis(i) for i in range(joystick.get_numaxes())]
                btns = [bool(joystick.get_button(i)) for i in range(joystick.get_numbuttons())]
                hats = [joystick.get_hat(i) for i in range(joystick.get_numhats())]

                rtn_axes = {
                    "LEFT_X": axis(axes[0]),
                    "LEFT_Y": axis(axes[1]),
                    "RIGHT_X": axis(axes[3]),
                    "RIGHT_Y": axis(axes[4]),
                    "LEFT_TRIGGER": axes[2],
                    "RIGHT_TRIGGER": axes[5]
                }

                if is_win:
                    rtn_axes["RIGHT_X"], rtn_axes["RIGHT_Y"], rtn_axes["LEFT_TRIGGER"] = (
                        rtn_axes["LEFT_TRIGGER"], rtn_axes["RIGHT_X"], rtn_axes["RIGHT_Y"])

                if is_xbox:
                    rtn_btns = {
                        "RIGHT_D": btns[0],
                        "RIGHT_R": btns[1],
                        "RIGHT_L": btns[2],
                        "RIGHT_U": btns[3],
                        "LB": btns[4],
                        "LT": rtn_axes["LEFT_TRIGGER"] > consts.JOYSTICK_TRIGGER_A2D_THRESHOLD,
                        "RB": btns[5],
                        "RT": rtn_axes["RIGHT_TRIGGER"] > consts.JOYSTICK_TRIGGER_A2D_THRESHOLD,
                        "SELECT_BTN": btns[6],
                        "START_BTN": btns[7],
                        "MODE_BTN": btns[8],
                        "LEFT_THUMB": btns[9],
                        "RIGHT_THUMB": btns[10],
                        "LEFT_D": hats[0][1] == -1,
                        "LEFT_U": hats[0][1] == 1,
                        "LEFT_L": hats[0][0] == -1,
                        "LEFT_R": hats[0][0] == 1
                    }

                    if is_win:
                        rtn_btns["MODE_BTN"], rtn_btns["LEFT_THUMB"], rtn_btns["RIGHT_THUMB"] = (
                            False, rtn_btns["MODE_BTN"], rtn_btns["LEFT_THUMB"])

                else:
                    if is_win:
                        rtn_btns = {
                            "RIGHT_D": btns[0],
                            "RIGHT_R": btns[1],
                            "RIGHT_L": btns[2],
                            "RIGHT_U": btns[3],
                            "LB": btns[9],
                            "LT": axes[4] > consts.JOYSTICK_TRIGGER_A2D_THRESHOLD,
                            "RB": btns[10],
                            "RT": axes[5] > consts.JOYSTICK_TRIGGER_A2D_THRESHOLD,
                            "SELECT_BTN": btns[4],
                            "START_BTN": btns[6],
                            "MODE_BTN": btns[5],
                            "LEFT_THUMB": btns[7],
                            "RIGHT_THUMB": btns[8],
                            "LEFT_U": btns[11],
                            "LEFT_D": btns[12],
                            "LEFT_L": btns[13],
                            "LEFT_R": btns[14]
                        }
                    else:
                        rtn_btns = {
                            "RIGHT_D": btns[0],
                            "RIGHT_R": btns[1],
                            "RIGHT_L": btns[3],
                            "RIGHT_U": btns[2],
                            "LB": btns[4],
                            "LT": rtn_axes["LEFT_TRIGGER"] > consts.JOYSTICK_TRIGGER_A2D_THRESHOLD,
                            "RB": btns[5],
                            "RT": rtn_axes["RIGHT_TRIGGER"] > consts.JOYSTICK_TRIGGER_A2D_THRESHOLD,
                            "SELECT_BTN": btns[8],
                            "START_BTN": btns[9],
                            "MODE_BTN": btns[10],
                            "LEFT_THUMB": btns[11],
                            "RIGHT_THUMB": btns[12],
                            "LEFT_D": hats[0][1] == -1,
                            "LEFT_U": hats[0][1] == 1,
                            "LEFT_L": hats[0][0] == -1,
                            "LEFT_R": hats[0][0] == 1
                        }

                gb.write("opcontrol.joystick", {
                    "available": True,
                    "update": time.perf_counter(),
                    "axes": rtn_axes,
                    "btns": rtn_btns
                })

                time.sleep(consts.JOYSTICK_UPDATE_MINIMUM_INTERVAL)

            logger.warning("All joystick disconnected")
        except KeyboardInterrupt:
            break
        except:
            logger.error("Joystick loop error", exc_info=True)

    pygame.quit()
