from typing import Callable, Optional, Tuple, Union, cast
from types import ModuleType

import crc8
import msgpack
import marshal
from cobs import cobs
from .tools import *

PkgIdxType = Union[int, bytes]

# https://gitlab.com/-/ide/project/advian-oss/python-msgpacketizer/tree/master/-/src/msgpacketizer/packer.py/


class PacketEncoder:

    def pack(pkg_type: int, data_in: bytes) -> bytes:
        """Pack into msgpacketizer compatible binary, does not include the field separator null byte"""
        check = crc8.crc8()
        check.update(data_in)
        return cobs.encode(bytes([pkg_type]) + data_in + check.digest())

    def unpack(bytes_in: bytes) -> Tuple[int, bytes]:
        """unpack from msgpacketizer binary, can deal with the trailing/preceding null byte if needed"""
        if bytes_in[0] == 0:
            bytes_in = bytes_in[1:]
        if bytes_in[-1] == 0:
            bytes_in = bytes_in[:-1]
        decoded = cobs.decode(bytes_in)
        idx = decoded[0]
        pkg_crc = decoded[-1]
        data = decoded[1:-1]
        check = crc8.crc8()
        check.update(data)
        expected_crc = check.digest()[0]
        if expected_crc != pkg_crc:
            raise ValueError("packet checksum {} does not match expected {}".format(pkg_crc, expected_crc))
        return (idx, data)


class Packet:
    PACKET_ID = 256

    def encode(self, payload: bytes):
        self.payload = payload
        self.data = PacketEncoder.pack(self.PACKET_ID, payload)
        return self

    def decode(self, payload: bytes):
        self.payload = payload
        return self


class DiffPacket(Packet):
    PACKET_ID = 3

    def encode(self, path: str, change: any):
        self.path = path
        self.change = change

        payload = bytes(path, "ascii") + bytes([0]) + msgpack.packb(change)
        return super().encode(payload)

    def encode_diff(self, diff: Diff):
        return self.encode(diff.path, diff.change)

    def decode(self, payload: bytes):
        end = payload.find(0)
        self.path = payload[:end].decode("ascii")
        self.change = msgpack.unpackb(payload[end + 1:], use_list=True)
        return super().decode(payload)


class MarshalDiffPacket(Packet):
    PACKET_ID = 5

    def encode(self, path: str, change: any):
        self.path = path
        self.change = change

        payload = bytes(path, "ascii") + bytes([0]) + marshal.dumps(change)
        return super().encode(payload)

    def encode_diff(self, diff: Diff):
        return self.encode(diff.path, diff.change)

    def decode(self, payload: bytes):
        end = payload.find(0)
        self.path = payload[:end].decode("ascii")
        self.change = marshal.loads(payload[end + 1:])
        return super().decode(payload)


class MarshalDiffBroadcastPacket(Packet):
    PACKET_ID = 6

    def encode(self, diff_id: int, path: str, change: any):
        self.diff_id = diff_id
        self.path = path
        self.change = change

        payload = int(self.diff_id).to_bytes(4, "little") + bytes(path, "ascii") + bytes([0]) + marshal.dumps(change)
        return super().encode(payload)

    def encode_diff(self, diff: Diff):
        return self.encode(diff.diff_id, diff.path, diff.change)

    def decode(self, payload: bytes):
        self.diff_id = int.from_bytes(payload[:4], "little")
        end = payload.find(0, 4)
        self.path = payload[4:end].decode("ascii")
        self.change = marshal.loads(payload[end + 1:])
        return super().decode(payload)


class DownstreamBoundPacket(Packet):
    pass


class GatewayIdentityU2DPacket(DownstreamBoundPacket):
    PACKET_ID = 2

    def encode(self, conn_id: str):
        self.conn_id = conn_id

        payload = bytes(conn_id, "ascii") + bytes([0])
        return super().encode(payload)

    def decode(self, payload: bytes):
        self.conn_id = payload.decode("ascii")[:-1]
        return super().decode(payload)


class UpstreamBoundPacket(Packet):
    pass


class DebugMessageD2UPacket(UpstreamBoundPacket):
    PACKET_ID = 4

    def encode(self, message: str):
        self.message = message

        payload = bytes(message, "ascii") + bytes([0])
        return super().encode(payload)

    def decode(self, payload: bytes):
        self.message = payload.decode("ascii")[:-1]
        return super().decode(payload)


class HelloD2UPacket(UpstreamBoundPacket):
    PACKET_ID = 1

    def encode(self):
        return super().encode(bytes([0]))

    def decode(self, payload: bytes):
        return super().decode(payload)


class DiffOrigin:

    def __init__(self):
        self.ignored_diff_id: set[int] = set()
        self.diff_packet_type: type[Packet] = None

    def _sync_exact_match(self, diff: Diff, packet: Packet, early: bool = False):
        pass


class PacketOrigin:

    def _decode_packet(self, in_raw: bytes, available_packets: list[type[Packet]]) -> Packet:
        packet_id, data = PacketEncoder.unpack(in_raw)
        # might raise IndexError
        packet_class: type[Packet] = [p for p in available_packets if p.PACKET_ID == packet_id][0]
        return packet_class().decode(data)

    def read(self, in_raw: bytes):
        pass

    def write(self, packet: Packet):
        pass
