from typing import Union, Callable, Optional, Tuple, cast

import crc8
import msgpack
import marshal
from cobs import cobs

PkgIdxType = Union[int, bytes]

# https://gitlab.com/-/ide/project/advian-oss/python-msgpacketizer/tree/master/-/src/msgpacketizer/packer.py/


class PacketEncoder:

    def normalize_pkg_type(pkg_type: PkgIdxType) -> bytes:
        """Normalize pkg type to bytes"""
        if not isinstance(pkg_type, (int, bytes)):
            raise ValueError("Packet type must be int (0-255) or byte")
        if isinstance(pkg_type, int):
            pkg_type = bytes([pkg_type])
        if len(pkg_type) != 1:
            raise ValueError("Packet type must be exactly one byte")
        return pkg_type

    def pack(pkg_type: PkgIdxType, data_in: bytes) -> bytes:
        """Pack into msgpacketizer compatible binary, does not include the field separator null byte"""
        pkg_type = PacketEncoder.normalize_pkg_type(pkg_type)
        check = crc8.crc8()
        check.update(data_in)
        return cobs.encode(pkg_type + data_in + check.digest())

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
    data: bytes
    payload: bytes

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

    def decode(self, payload: bytes):
        end = payload.find(0)
        self.path = payload[:end].decode("ascii")
        self.change = msgpack.unpackb(payload[end + 1:], use_list=True)
        return self


class MarshalDiffPacket(Packet):
    PACKET_ID = 5

    def encode(self, path: str, change: any):
        self.path = path
        self.change = change

        payload = bytes(path, "ascii") + bytes([0]) + marshal.dumps(change)
        return super().encode(payload)

    def decode(self, payload: bytes):
        end = payload.find(0)
        self.path = payload[:end].decode("ascii")
        self.change = marshal.loads(payload[end + 1:])
        return self


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

        payload = bytes(message, "ascii")
        return super().encode(payload)

    def decode(self, payload: bytes):
        self.message = payload.decode("ascii")[:-1]
        return self


class HelloD2UPacket(UpstreamBoundPacket):
    PACKET_ID = 1

    def encode(self):
        return super().encode(bytes([0]))

    def decode(self, payload: bytes):
        return super().decode(payload)