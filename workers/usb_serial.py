
import time
from core.usb_serial import SerialConnectionManager

import globals as gb


manager = SerialConnectionManager()

def run(share):
    gb.share = share

    while True:
        manager.loop()

        time.sleep(0.001)