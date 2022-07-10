from typing import Union, Callable, Tuple, Any, cast

import io
import serial
import time
import threading
import os

import crc8
import msgpack
from cobs import cobs

import globals as gb

PkgIdxType = Union[int, bytes]

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


class SerialConnection:
    s: serial.Serial

    serial_rx = [0] * 2048
    serial_rx_index = 0

    def __init__(self, path: str, name: str):
        self.name = name
        self.s = serial.Serial(port=path, baudrate=115200, timeout=.1)

    def write(self, packet: DeviceBoundPacket):
        # print("send bytes", packet.data + bytes([0]))
        self.s.write(packet.data + bytes([0]))

    def read(self, buf: bytes):
        try:
            packet_id, data = unpack(buf)
            
            packet_class = [p for p in [DataPatchD2HPacket, DebugMessageD2HPacket] if p.PACKET_ID == packet_id][0]

            packet = packet_class(data)

            if packet_class is DataPatchD2HPacket:
                old_val = False

                if packet.path == "serial." + self.name + ".watch":
                    old_val = gb.read("packet.path") or []
                    pass

                # print("change", packet.path, packet.receive)
                gb.write(packet.path, packet.receive, True)

                if old_val is not False:
                    new_watchers = set(gb.read(packet.path)) - set(old_val)
                    for watcher in new_watchers:
                        self.write(DataPatchH2DPacket(watcher,  gb.read(watcher)))

            if packet_class is DebugMessageD2HPacket:
                print("Arduino: {}".format(packet.message)) # TODO

        except BaseException as e:
            print("error buffer", buf)
            print("Decode packet error, ignored.", e)


class SerialConnectionManager:
    boards: dict[str, SerialConnection] = {}

    last_connect_attempt = 0

    def connect(self):
        self.last_connect_attempt = time.time()

        dev_list = os.listdir("/dev")

        tty_list = []
        for f in dev_list:
            if f.startswith("ttyACM"):
                tty_list.append(f)

        for f in tty_list:
            if f in self.boards:
                if not self.boards[f].s.isOpen():
                    try:
                        self.boards[f].s.open()
                        print("reopen port", f)
                    except:
                        print("Unable to open port")
            else:
                try:
                    self.boards[f] = SerialConnection("/dev/" + f, f)

                    time.sleep(1) # TODO

                    self.boards[f].write(DeviceIdentityH2DPacket(f))
                    gb.write("serial." + f, {"available": True, "watch": []})

                    print("Open port", f)
                except:
                    try:
                        os.system("echo %s|sudo -S %s" % ("robocon", "chmod 666 /dev/" + f))
                        print("sudo chmod port", f)
                    except:
                        print("Unable to chmod port", f)

        # print(tty_list)

    def loop(self):
        if time.time() - self.last_connect_attempt > 1:
            self.connect()

        for board_name in list(self.boards.keys()):
            board = self.boards[board_name]
            if not board.s.isOpen():
                continue

            try:
                while board.s.inWaiting():
                    buf = board.s.read(1)

                    board.serial_rx[board.serial_rx_index] = int(buf[0])
                    board.serial_rx_index += 1

                    if int(buf[0]) == 0:
                        board.read(bytes(board.serial_rx[0: board.serial_rx_index]))
                        board.serial_rx_index = 0

            except BaseException as e:
                print("Read error, close port", board_name, e)
                board.s.close()
                del self.boards[board_name]
                gb.write("serial." + board_name, {"available": False, "watch": []})


        diffs = gb.share["__diff__"]
        serials = gb.read("serial")
        while len(diffs) != 0:
            diff = diffs[0]

            for board_name, board_info in serials.items():
                for watcher in board_info["watch"]:
                    if diff.startswith(watcher) or watcher.startswith(diff):
                        # print("send patch to", board_name, watcher, gb.read(watcher))
                        self.boards[board_name].write(DataPatchH2DPacket(watcher,  gb.read(watcher)))

            del diffs[0]
