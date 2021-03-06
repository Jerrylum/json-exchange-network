from tkinter import *
from tkinter import ttk

import globals as gb

import time


def run(share):
    gb.share = share

    gb.write('opcontrol.keyboard.keys', {})

    attention = {}

    def onKeyPress(event):
        if event.keysym in attention and time.perf_counter() - attention[event.keysym] < 0.01:
            del attention[event.keysym]
            return
        else:
            gb.write('opcontrol.keyboard.keys.' + str(event.keysym), True)

    def onKeyRelease(event):
        attention[event.keysym] = time.perf_counter()

    def keyDebouncing():
        for key in list(attention.keys()):
            if time.perf_counter() - attention[key] > 0.01:
                del attention[key]
                gb.write('opcontrol.keyboard.keys.' + str(key), False)

        root.after(5, keyDebouncing)

    root = Tk()
    root.geometry('100x100-0-0')
    root.title('Keystroke Listener')
    root.bind('<KeyPress>', onKeyPress)
    root.bind('<KeyRelease>', onKeyRelease)
    root.after(0, keyDebouncing)
    root.mainloop()
