import threading
import time


def run(method):
    threading.Thread(target=method).start()


def wait(ms):
    time.sleep(ms / 1000)


class Clock:
    def __init__(self, frequency: int, busyWait=False, offset=0.00015):
        self.period = 1 / frequency
        self.last_time = time.perf_counter()
        self.busyWait = busyWait
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
