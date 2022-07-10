
import time
from core.usb_serial import SerialConnectionManager


manager = SerialConnectionManager()

def run():
    while True:
        manager.loop()

        time.sleep(0.001)