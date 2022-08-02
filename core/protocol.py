from typing import Union, Callable, Tuple, Any, cast

import crc8
import msgpack
from cobs import cobs

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
    payload: bytes

    def encode(self, payload: bytes):
        self.payload = payload
        self.data = pack(self.PACKET_ID, payload)
        return self

    def decode(self, payload: bytes):
        self.payload = payload
        return self


class DeviceBoundPacket(Packet):
    pass


class DeviceIdentityH2DPacket(DeviceBoundPacket):
    PACKET_ID = 1

    def encode(self, device_path: str):
        self.device_path = device_path

        payload = bytes(device_path, "ascii") + bytes([0])
        return super().encode(payload)

    def decode(self, payload: bytes):
        self.device_path = payload.decode("ascii")[:-1]
        return super().decode(payload)

# import time

class DataPatchH2DPacket(DeviceBoundPacket):
    PACKET_ID = 3

    def encode(self, path: str, send: any):
        self.path = path
        self.send = send

        # if path == "rg.o":
        #     print("send", time.perf_counter())

        payload = bytes(path, "ascii") + bytes([0]) + msgpack.packb(send)
        return super().encode(payload)

    def decode(self, payload: bytes):
        end = payload.find(0)
        self.path = payload[:end].decode("ascii")
        self.send = msgpack.unpackb(payload[end + 1:], use_list=True, encoding='ascii')
        return self


class HostBoundPacket(Packet):
    pass


class DataPatchD2HPacket(HostBoundPacket):
    PACKET_ID = 2

    def encode(self, path: str, receive: any):
        self.path = path
        self.receive = receive

        payload = bytes(path, "ascii") + bytes([0]) + msgpack.packb(receive)

        print("payload", payload)
        return super().encode(payload)

    def decode(self, payload: bytes):
        end = payload.find(0)
        self.path = payload[:end].decode("ascii")
        self.receive = msgpack.unpackb(payload[end + 1:], use_list=True, encoding='ascii')

        return self


class DebugMessageD2HPacket(HostBoundPacket):
    PACKET_ID = 4

    def encode(self, message: str):
        self.message = message

        payload = bytes(message, "ascii")
        return super().encode(payload)

    def decode(self, payload: bytes):
        self.message = payload.decode("ascii")[:-1]
        return self
