import sys
sys.path.insert(1, './')

from jen import *
import random
import pytest


def test_packet_encoder_packing():
    for i in range(2048):
        data = bytes(random.getrandbits(8) for _ in range(i))
        type = random.randint(0, 255)

        packed = PacketEncoder.pack(type, data)
        a = PacketEncoder.unpack(packed)
        b = PacketEncoder.unpack(packed + b"\x00")
        c = PacketEncoder.unpack(b"\x00" + packed)
        d = PacketEncoder.unpack(b"\x00" + packed + b"\x00")
        assert (type, data) == a == b == c == d


def test_packet_encoder_checksum_error():
    for i in range(2048):
        data = bytes(random.getrandbits(8) for _ in range(i))
        type = random.randint(0, 255)

        packed = PacketEncoder.pack(type, data)
        assert (type, data) == PacketEncoder.unpack(packed)

        packed_b = bytearray(packed)
        # XXX: following hideakitai/Packetizer implementation
        # packet type is not included in the checksum
        # therefore, the first 2 bytes are not checked
        j = random.randint(2, 2 + i)
        packed_b[j] = (packed_b[j] + 1) % 256

        with pytest.raises(Exception):
            PacketEncoder.unpack(bytes(packed_b))


def test_hello_packet():
    assert HelloD2UPacket().encode().data == b"\x02\x01\x01\x01"
    assert HelloD2UPacket().decode(b"\x00").payload == b"\x00"


def test_gateway_identity_packet():
    for i in range(512):
        identity = "".join(chr(random.randint(1, 127)) for _ in range(i))

        e = GatewayIdentityU2DPacket().encode(identity)
        d = GatewayIdentityU2DPacket().decode(PacketEncoder.unpack(e.data)[1])

        del e.__dict__["data"]
        assert e.__dict__ == d.__dict__


def test_diff_packet():
    for i in range(512):
        path = "".join(chr(random.randint(1, 127)) for _ in range(i // 2))
        change = ["test"] * i

        e = DiffPacket().encode(path, change)
        d = DiffPacket().decode(PacketEncoder.unpack(e.data)[1])

        del e.__dict__["data"]
        assert e.__dict__ == d.__dict__


def test_debug_message_packet():
    for i in range(512):
        message = "".join(chr(random.randint(1, 127)) for _ in range(i))

        e = DebugMessageD2UPacket().encode(message)
        d = DebugMessageD2UPacket().decode(PacketEncoder.unpack(e.data)[1])

        del e.__dict__["data"]
        assert e.__dict__ == d.__dict__


def test_marshal_diff_packet():
    for i in range(512):
        path = "".join(chr(random.randint(1, 127)) for _ in range(i // 2))
        change = ["test"] * i

        e = MarshalDiffPacket().encode(path, change)
        d = MarshalDiffPacket().decode(PacketEncoder.unpack(e.data)[1])

        del e.__dict__["data"]
        assert e.__dict__ == d.__dict__


def test_marshal_diff_broadcast_packet():
    for i in range(512):
        path = "".join(chr(random.randint(1, 127)) for _ in range(i // 2))
        change = ["test"] * i

        e = MarshalDiffBroadcastPacket().encode(random.randint(0, 0xFFFFFFFF), path, change)
        d = MarshalDiffBroadcastPacket().decode(PacketEncoder.unpack(e.data)[1])

        del e.__dict__["data"]
        assert e.__dict__ == d.__dict__
