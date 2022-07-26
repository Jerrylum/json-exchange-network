
import threading
import time

import globals as gb

from core.device import RemoteDevice


def start_thread(method):
    threading.Thread(target=method).start()


def wait(ms):
    time.sleep(ms / 1000)


class Clock:
    def __init__(self, frequency: int, busyWait=False, offset=0.00015):
        self.period = 1 / frequency
        self.last_time = time.perf_counter()
        self.busy_wait = busyWait
        self.offset = offset
        self.sleep = self.period - self.offset

        if busyWait:
            self.spin = self._spin_bw

    def spin(self):
        time.sleep(max(0, self.sleep - (time.perf_counter() - self.last_time)))
        self.last_time = time.perf_counter()

    def _spin_bw(self):
        time.sleep(max(0, self.sleep - (time.perf_counter() - self.last_time)))

        while time.perf_counter() - self.last_time < self.period:
            pass

        self.last_time = time.perf_counter()


class TpsCounter:
    def __init__(self):
        self._last_sec_timestamp = 0
        self._tps = 0
        self._count = 0

    def tick(self):
        now_timestamp = time.perf_counter()
        if (now_timestamp - self._last_sec_timestamp) > 1:
            self._last_sec_timestamp = now_timestamp
            self._tps = self._count
            self._count = 0
        self._count += 1

    def tps(self):
        return self._tps


class WorkerController:
    _devices: dict[str, RemoteDevice] = {}
    _clock: Clock = None

    name: str = None
    serial_manager = None
    shared_data = None

    def __init__(self, name: str, shared_data: dict):
        from core.usb_serial import SerialConnectionManager

        self.name = name
        self.serial_manager = SerialConnectionManager(self)
        self.shared_data = shared_data

    def init(self):
        gb.share = self.shared_data
        gb.current_worker = self

    def use_clock(self, frequency: int, busyWait=False, offset=0.0004):
        self._clock = Clock(frequency, busyWait, offset)

    def spin(self):
        self.serial_manager.spin()
        self._clock.spin()
