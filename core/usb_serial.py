

import io
import serial
import serial.tools.list_ports
import time
import threading
import os
import traceback

from core.device import *
from core.protocol import *
from core.tools import *
from serial.tools.list_ports_common import ListPortInfo
from consts import *


import globals as gb

class PortInfo:
    device: str = None
    vid: str = None
    pid: str = None
    serial_number: str = None

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    def match(self, other: ListPortInfo):
        for key in self.__dict__:
            if key not in other.__dict__:
                return False
            if self.__dict__[key] != other.__dict__[key]:
                return False
        return True


class SerialConnection(RemoteDevice):
    manager: any
    s: serial.Serial
    start_at: float
    init: bool

    write_lock = threading.Lock()
    serial_rx = [0] * 2048
    serial_rx_index = 0

    def __init__(self, path: str, manager: any):
        super().__init__(path)
        self.manager = manager
        self.start_at = time.perf_counter()
        self.init = False
        self.s = serial.Serial(port=path, baudrate=115200)
        gb.write("device." + self.name, {"available": False, "type": "serial", "watch": []})
        self.open = True

        def read_thread():
            try:
                time.sleep(0.5)

                while self.s.inWaiting() > 0: # IMPORTANT: Clear the buffer before reading
                    buf = self.s.read(self.s.inWaiting())

                self.write(DeviceIdentityH2DPacket().encode(self.name))
                gb.write("device." + self.name + ".available", True)
                self.manager.update_device_info()
                self.init = True
                logger.info("Serial device %s initialized" % self.name)

                while self.open:
                    buf = int(self.s.read(1)[0])
                    self.serial_rx[self.serial_rx_index] = buf
                    self.serial_rx_index += 1

                    if buf == 0:
                        self.read(bytes(self.serial_rx[0: self.serial_rx_index]))
                        self.serial_rx_index = 0
            except:
                logger.error("Error in \"%s\" read thread" % self.name, exc_info=True)
                self.manager.disconnect(self.name)

        threading.Thread(target=read_thread).start()

    def close(self):
        self.open = False
        self.s.close()
        gb.write("device." + self.name, {"available": False, "type": "serial", "watch": []})

    def watch_update(self, path: str, val):
        self.write(DataPatchH2DPacket().encode(path, val))

    def write(self, packet: DeviceBoundPacket):
        # print("send bytes", packet.data + bytes([0]))
        with self.write_lock:
            # print("Packet size:", len(packet.data))
            self.s.write(packet.data + bytes([0]))

    def read(self, buf: bytes):
        try:
            packet_id, data = unpack(buf)

            packet_class = [p for p in [DataPatchD2HPacket, DebugMessageD2HPacket] if p.PACKET_ID == packet_id][0]

            packet = packet_class().decode(data)

            if packet_class is DataPatchD2HPacket:
                old_watchers = False

                if packet.path == "device." + self.name + ".watch":
                    old_watchers = gb.read(packet.path) or []

                # print("received size", len(buf))
                # print("change", packet.path, packet.receive)
                gb.write(packet.path, packet.receive)

                if old_watchers is not False:
                    diff_watchers = set(gb.read(packet.path)) - set(old_watchers)
                    for watcher in diff_watchers:
                        self.write(DataPatchH2DPacket().encode(watcher, gb.read(watcher)))
                    
                    self.manager.update_device_info()

            if packet_class is DebugMessageD2HPacket:
                # print("f", time.perf_counter())
                # print("Arduino: {} {}".format(packet.message, time.perf_counter()))  # TODO
                print("Arduino: {}".format(packet.message))  # TODO

        except BaseException:
            print("error buffer", buf)
            logger.error("Error in \"%s\" read thread" % self.name, exc_info=True)


class SerialConnectionManager:

    _worker: WorkerController

    whitelist: list[PortInfo] = []
    started = False

    ignored_update = set()
    last_connect_attempt = 0
    last_device_info = {}
    last_handled_diff = 0

    def __init__(self, worker: WorkerController):
        self._worker = worker

    def try_change_port_permission(self, path: str):
        try:
            os.system("echo %s|sudo -S %s" % ("robocon", "chmod 666 " + path))
            print("sudo chmod port", path)
        except:
            print("Unable to chmod port", path)

    def update_device_info(self):
        self.last_device_info = {k: v for k, v in dict(gb.read("device")).items()
                                 if k in self._worker._devices and type(self._worker._devices[k]) is SerialConnection}

    def connect(self):
        self.last_connect_attempt = time.perf_counter()

        tty_list = [p for p in list(serial.tools.list_ports.comports()) if p.device not in PORT_BLACKLIST]

        tty_list = [p for p in tty_list if any(w.match(p) for w in self.whitelist)]

        for f in tty_list:
            if f.device in list(self._worker._devices.keys()):
                continue

            deviceInfo = gb.read("device." + f.device)
            if deviceInfo is not None and deviceInfo["available"] == True:
                continue

            try:
                self._worker._devices[f.device] = SerialConnection(f.device, self)
                self.update_device_info()
                logger.info("Serial device %s (%s) connected" % (f.device, f.serial_number))
            except:
                self.try_change_port_permission(f)

    def disconnect(self, name: str):
        if name in self._worker._devices and type(self._worker._devices[name]) is SerialConnection:
            try: # XXX: ignoring race condition
                self._worker._devices[name].close()
                del self._worker._devices[name]     
            except:
                pass     
            self.update_device_info()
            logger.warning("Serial device %s disconnected" % name)

    def start_listening(self):
        if self.started:
            return
        self.started = True

        def sync_thread():
            condition: threading.Condition = gb.share['__diff_condition__']
            while self.started:
                with condition:
                    condition.wait()
                    self.sync()

        threading.Thread(target=sync_thread).start()

    def stop_listening(self):
        self.started = False

        [self.disconnect(k) for k in list(self._worker._devices.keys())]

    def spin(self):
        if self.started and time.perf_counter() - self.last_connect_attempt > 1:
            self.connect()

    def _sync_exact_match(self, diff, val):
        self.ignored_update.add(diff["uuid"])
        for device_name, device_info in self.last_device_info.items():
            [self._worker._devices[device_name].watch_update(watcher, val) for watcher in device_info["watch"]
                if diff["path"] == watcher]

    def _sync_related(self, diff):
        path = diff["path"]
        for device_name, device_info in self.last_device_info.items():
            [self._worker._devices[device_name].watch_update(watcher, gb.read(watcher)) for watcher in device_info["watch"]
                if (path.startswith(watcher) or watcher.startswith(path)) and path != watcher]

    def sync(self):
        all_diffs = gb.share["__diff__"]

        diffs = []
        last_handled = None
        for i in range(DIFF_QUEUE_SIZE, 0, -1): # XXX: ignore race condition
            diff = all_diffs[i - 1]
            if diff["uuid"] == self.last_handled_diff or diff["uuid"] == 0:
                break
            if last_handled is None:
                last_handled = diff["uuid"]
            if diff["uuid"] in self.ignored_update:
                self.ignored_update.remove(diff["uuid"])
                continue
            diffs.insert(0, diff)

        if last_handled is not None:
            self.last_handled_diff = last_handled

        # ~1ms passed

        for diff in diffs:
            for device_name, device_info in self.last_device_info.items():
                [self._worker._devices[device_name].watch_update(watcher, gb.read(watcher)) for watcher in device_info["watch"]
                    if diff["path"].startswith(watcher) or watcher.startswith(diff["path"])]
