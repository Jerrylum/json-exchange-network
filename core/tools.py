
import logging
import threading
import time
from typing import Optional
import uuid

import consts

import globals as gb


Address = tuple[str, int]


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

    def __init__(self, name: str, shared_data: dict):
        from core.gateway import GatewayManager

        self.name = name
        self.display_name = ''.join(word.title() for word in name.split('_'))
        self.shared_data = shared_data
        self.managers: list[GatewayManager] = []
        self.clock: Optional[Clock] = None

        logger.info("Worker \"%s\" registered" % self.display_name)

    def init(self):
        gb.sync_condition = threading.Condition()
        gb.share = self.shared_data
        gb.current_worker = self
        gb.gateways = []
        gb.early_gateways = []

        logger.name = self.display_name

        logger.info("Worker started")

    def use_clock(self, frequency: int, busy_wait=False, offset=0.0004):
        self.clock = Clock(frequency, busy_wait, offset)
        return self.clock

    def use_serial_manager(self):
        from core.tty import SerialConnectionManager

        m = SerialConnectionManager(self)
        self.managers.append(m)
        return m

    def spin(self):
        [m.spin() for m in self.managers]
        if self.clock is not None:
            self.clock.spin()


class Diff:

    def __init__(self, uuid: int, path: str, change: any):
        self.uuid: int = uuid
        self.path: str = path
        self.change = change

    def __eq__(self, other):
        if type(other) is type(self):
            return self.uuid == other.uuid
        else:
            return False

    def __hash__(self):
        return self.uuid

    def match(self, path: str):
        return self.path == path or path == "*" or (path.endswith(".*") and self.path.startswith(path[:-2]))

    def related(self, path: str):
        return path.startswith(self.path) or self.path.startswith(path)

    def placeholder():
        return Diff(0, "__placeholder__", None)

    def build(path: str, change: any):
        return Diff(uuid.uuid4().int >> (128 - 32), path, change)


class DiffOrigin:
    def __init__(self):
        self.ignored_diff_id: set[int] = set()


class CustomFormatter(logging.Formatter):
    grey = "\x1b[38;20m"
    yellow = "\x1b[33;20m"
    red = "\x1b[31;20m"
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

    def getLoggerHandler():
        handler = logging.StreamHandler()
        handler.setLevel(logging.INFO)
        handler.setFormatter(CustomFormatter())
        return handler


logger = logging.getLogger("Main")
logger.name
logger.setLevel(logging.DEBUG)
logger.addHandler(CustomFormatter.getLoggerHandler())
# fh = logging.FileHandler('latest.log')
# fh.setLevel(logging.DEBUG)
# logger.addHandler(fh)
