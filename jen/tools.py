
import logging
import threading
import os
import time
import uuid


Address = tuple[str, int]


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


class Diff:

    def __init__(self, uuid: int, path: str, change: any):
        self.diff_id: int = uuid
        self.path: str = path
        self.change = change

    def __eq__(self, other):
        if type(other) is type(self):
            return self.diff_id == other.diff_id
        else:
            return False

    def __hash__(self):
        return self.diff_id

    def match(self, path: str):
        return self.path == path or (path.endswith("*") and self.path.startswith(path[:-1]))

    def related(self, path: str):
        return path.startswith(self.path) or self.path.startswith(path)

    def placeholder():
        return Diff(0, "__placeholder__", None)

    def build(path: str, change: any):
        return Diff(uuid.uuid4().int >> (128 - 32), path, change)


class CustomFormatter(logging.Formatter):
    grey = "\x1b[38;20m"
    yellow = "\x1b[33;20m"
    red = "\x1b[31;20m"
    green = "\x1b[32;20m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"
    format1 = "[%(asctime)s] - [%(name)s/%(levelname)s]" + reset + ": %(message)s"

    FORMATS = {
        logging.DEBUG: grey + format1 + reset,
        logging.INFO: grey + format1 + reset,
        logging.WARNING: yellow + format1 + reset,
        logging.ERROR: red + format1 + reset,
        logging.CRITICAL: bold_red + format1 + reset
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt, "%s.%03d" % ("%H:%M:%S", record.msecs))
        return formatter.format(record)

    def get_logger_handler():
        handler = logging.StreamHandler()
        handler.setLevel(logging.INFO)
        handler.setFormatter(CustomFormatter())
        return handler


logger = logging.getLogger("Main")
logger.setLevel(logging.DEBUG)
logger.addHandler(CustomFormatter.get_logger_handler())
# fh = logging.FileHandler('latest.log')
# fh.setLevel(logging.DEBUG)
# logger.addHandler(fh)
