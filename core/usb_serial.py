from typing import Union, Callable, Tuple, Any, cast

import io
import serial
import serial.tools.list_ports
import time
import threading
import os

import crc8
import msgpack
from cobs import cobs
from core.device import RemoteDevice
from core.tools import WorkerController
from serial.tools.list_ports_common import ListPortInfo
from consts import *


import globals as gb

PkgIdxType = Union[int, bytes]

PORT_BLACKLIST = ["/dev/ttyAMA0", "COM1"]

# https://gitlab.com/-/ide/project/advian-oss/python-msgpacketizer/tree/master/-/src/msgpacketizer/packer.py/


def normalize_pkgidx(pkgidx: PkgIdxType) -> bytes:
    """Normalize pkgidx to bytes"""
    if not isinstance(pkgidx, (int, bytes)):
        raise ValueError("pkgidx must be int (0-255) or byte")
    if isinstance(pkgidx, int):
        pkgidx = bytes([pkgidx])
    if len(pkgidx) != 1:
        raise ValueError("pkgidx must be exactly one byte")
    return pkgidx


def pack(pkgidx: PkgIdxType, datain: bytes) -> bytes:  # pylint: disable=E1136
    """Pack into msgpacketizer compatible binary, does not include the field separator null byte"""
    pkgidx = normalize_pkgidx(pkgidx)
    check = crc8.crc8()
    check.update(datain)
    return cast(bytes, cobs.encode(pkgidx + datain + check.digest()))


def unpack(bytesin: bytes) -> Tuple[int, Any]:
    """unpack from msgpacketizer binary, can deal with the trailing/preceding null byte if needed"""
    if bytesin[0] == 0:
        bytesin = bytesin[1:]
    if bytesin[-1] == 0:
        bytesin = bytesin[:-1]
    decoded = cobs.decode(bytesin)
    idx = decoded[0]
    pktcrc = decoded[-1]
    data = decoded[1:-1]
    check = crc8.crc8()
    check.update(data)
    expectedcrc = check.digest()[0]
    if expectedcrc != pktcrc:
        raise ValueError("packet checksum {} does not match expected {}".format(pktcrc, expectedcrc))
    return (idx, data)


class Packet:
    data: bytes

    def __init__(self, data: bytes):
        self.data = data


class DeviceBoundPacket(Packet):
    def __init__(self, data: bytes):
        super().__init__(pack(self.PACKET_ID, data))


class DeviceIdentityH2DPacket(DeviceBoundPacket):
    PACKET_ID = 1

    def __init__(self, device_path: str):
        payload = bytes(device_path, "ascii") + bytes([0])

        super().__init__(payload)


class DataPatchH2DPacket(DeviceBoundPacket):
    PACKET_ID = 3

    def __init__(self, path: str, send: any):
        payload = bytes(path, "ascii") + bytes([0]) + msgpack.packb(send)

        super().__init__(payload)


class HostBoundPacket(Packet):
    pass


class DataPatchD2HPacket(HostBoundPacket):
    PACKET_ID = 2

    def __init__(self, dataAfterCobs: bytes):
        super().__init__(dataAfterCobs)

        for i in range(0, len(dataAfterCobs)):
            if dataAfterCobs[i] == 0:
                self.path = dataAfterCobs[:i].decode("ascii")
                self.receive = msgpack.unpackb(
                    dataAfterCobs[i + 1:], use_list=True, encoding='ascii')
                break


class DebugMessageD2HPacket(HostBoundPacket):
    PACKET_ID = 4

    def __init__(self, dataAfterCobs: bytes):
        super().__init__(dataAfterCobs)

        self.message = dataAfterCobs.decode("ascii")


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
    s: serial.Serial
    start_at: float
    init: bool

    serial_rx = [0] * 2048
    serial_rx_index = 0

    def __init__(self, path: str):
        super().__init__(path)
        self.start_at = time.perf_counter()
        self.init = False
        self.s = serial.Serial(port=path, baudrate=115200, timeout=.1)

    def spin(self):
        if not self.init:
            if (time.perf_counter() - self.start_at) > 0.5:
                self.write(DeviceIdentityH2DPacket(self.name))
                gb.write("device." + self.name + ".available", True)
                self.init = True
                print("Init port", self.name)

                return True
            return False

        updated = False
        while self.s.inWaiting():
            buf = int(self.s.read(1)[0])
            self.serial_rx[self.serial_rx_index] = buf
            self.serial_rx_index += 1

            if buf == 0:
                updated = self.read(bytes(self.serial_rx[0: self.serial_rx_index])) or updated
                self.serial_rx_index = 0

        return updated

    def watch_update(self, path: str, val):
        self.write(DataPatchH2DPacket(path, val))

    def write(self, packet: DeviceBoundPacket):
        # print("send bytes", packet.data + bytes([0]))
        self.s.write(packet.data + bytes([0]))

    def read(self, buf: bytes):
        try:
            packet_id, data = unpack(buf)

            packet_class = [p for p in [DataPatchD2HPacket, DebugMessageD2HPacket] if p.PACKET_ID == packet_id][0]

            packet = packet_class(data)

            if packet_class is DataPatchD2HPacket:
                old_watchers = False

                if packet.path == "device." + self.name + ".watch":
                    old_watchers = gb.read(packet.path) or []

                # print("change", packet.path, packet.receive)
                gb.write(packet.path, packet.receive)

                if old_watchers is not False:
                    diff_watchers = set(gb.read(packet.path)) - set(old_watchers)
                    for watcher in diff_watchers:
                        self.write(DataPatchH2DPacket(watcher,  gb.read(watcher)))
                    return True
                return False
            if packet_class is DebugMessageD2HPacket:
                # print("f", time.perf_counter())
                print("Arduino: {}".format(packet.message))  # TODO

                return False

        except BaseException as e:
            print("error buffer", buf)
            print("Decode packet error, ignored.", e)
        return True


class SerialConnectionManager:

    _worker: WorkerController

    whitelist: list[PortInfo] = []

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
                self._worker._devices[f.device] = SerialConnection(f.device)
                gb.write("device." + f.device, {"available": False, "type": "serial", "watch": []})
                self.update_device_info()
                print("Open port", f.device, f.serial_number)
            except:
                self.try_change_port_permission(f)

    def spin(self):
        if time.perf_counter() - self.last_connect_attempt > 1:
            self.connect()

        updated = False

        for device_name in list(self._worker._devices.keys()):
            device = self._worker._devices[device_name]
            if type(device) is not SerialConnection:
                continue

            try:
                updated = device.spin() or updated
            except BaseException as e:
                print("Read error, close port", device_name, e)
                device.s.close()
                gb.write("device." + device_name, {"available": False, "type": "serial", "watch": []})
                del self._worker._devices[device_name]
                self.update_device_info()

        if updated:
            self.update_device_info()

        self.sync()

    def _sync_exact_match(self, diff, val):
        self.ignored_update.add(diff["uuid"])
        for device_name, device_info in self.last_device_info.items():
            # print("sync", time.perf_counter())
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
            if diff["uuid"] == self.last_handled_diff:
                break
            if last_handled is None:
                last_handled = diff["uuid"]
            if diff["uuid"] in self.ignored_update:
                self.ignored_update.remove(diff["uuid"])
                continue
            diffs.insert(0, diff)

        self.last_handled_diff = last_handled

        # ~1ms passed

        for diff in diffs:
            for device_name, device_info in self.last_device_info.items():
                [self._worker._devices[device_name].watch_update(watcher, gb.read(watcher)) for watcher in device_info["watch"]
                    if diff["path"].startswith(watcher) or watcher.startswith(diff["path"])]
