from sys import exc_info
import threading
import uuid
import yaml
import os
import socket
import threading
import time
import uuid

import consts

from core.protocol import *
from core.tools import *
from core.gateway import *

import globals as gb

class UDPConnection(GatewayConnection):

    def __init__(self, addr: Address, server: any):
        GatewayConnection.__init__(self)

        self.name = str(uuid.uuid4())[:8]
        self.addr = addr
        self.server = server

    def read(self, in_raw: bytes):
        packet_id, data = unpack(in_raw)

        if self.state == 0:
            available_packets = [HelloD2HPacket]
        elif self.state == 1:
            available_packets = [HelloD2HPacket, DataPatchPacket, DebugMessageD2HPacket]
        packet_class = [p for p in available_packets if p.PACKET_ID == packet_id][0] # TODO: error point

        packet = packet_class().decode(data)

        if packet_class is HelloD2HPacket:
            print("Send Identity", self.name, time.perf_counter())
            self.write(DataPatchPacket().encode("", gb.read("")))
            self.write(DeviceIdentityH2DPacket().encode(self.name))
            self.watching = []
            self.state = 1
        elif packet_class is DataPatchPacket:
            gb.write(packet.path, packet.change, False, self)

            if ("device." + self.name + ".watch").startswith(packet.path):
                self.watching = gb.read("device." + self.name + ".watch") or []

    def write(self, packet: Packet):
        # if type(packet) is DataPatchPacket:
        #     print(gb.current_worker.display_name if gb.current_worker else "(unknown)", self.name, packet.change)
        self.server.s.sendto(packet.data, self.addr)


class UDPServer(GatewayServerLike, Gateway):

    def __init__(self):
        GatewayServerLike.__init__(self)
        Gateway.__init__(self)

        self.s: socket.socket = None
        self.server_addr: Address = ("0.0.0.0", 7984)

        self.connections: dict[Address, UDPConnection] = {}

    def start_listening(self):
        if self.started:
            return
        self.started = True

        def server_thread():
            self.s = s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(self.server_addr)

            logger.info("UDP server started on %s:%d", *self.server_addr)

            while self.started:
                try:
                    in_raw, addr = s.recvfrom(2048)

                    if addr not in self.connections:
                        self.connections[addr] = UDPConnection(addr, self)

                    self.connections[addr].read(in_raw)
                except BaseException:
                    print("error buffer", in_raw)
                    logger.error("Error in server read thread", exc_info=True)

        def server_sync_thread():
            while self.started:
                with gb.sync_condition:
                    gb.sync_condition.wait()
                self._sync()

        threading.Thread(target=server_thread).start()
        threading.Thread(target=server_sync_thread).start()


class UDPClient(GatewayConnection, Gateway):

    def __init__(self, addr: Address):
        GatewayConnection.__init__(self)
        Gateway.__init__(self)

        self.s: socket.socket = None

        self.server_addr = addr

    def read(self, in_raw: bytes):
        packet_id, data = unpack(in_raw)

        if self.state == 0:
            available_packets = [DeviceIdentityH2DPacket, DataPatchPacket]
        elif self.state == 1:
            available_packets = [DeviceIdentityH2DPacket, DataPatchPacket]
        packet_class = [p for p in available_packets if p.PACKET_ID == packet_id][0]


        packet = packet_class().decode(data)

        if packet_class is DeviceIdentityH2DPacket and self.state == 0:
            self.name = packet.device_path
            self.state = 1
            logger.info("Registered \"%s\" gateway", self.name)

            gb.write("device." + self.name, {
                "available": True,
                "worker_name": gb.current_worker.display_name if gb.current_worker else "(unknown)",
                "type": "udp",
                "watch": self.watching
            })
        elif packet_class is DataPatchPacket:
            gb.write(packet.path, packet.change, False, self)
    
    def write(self, packet: Packet):
        # if type(packet) is DataPatchPacket:
        #     print(gb.current_worker.display_name if gb.current_worker else "(unknown)", packet.change)
        self.s.sendto(packet.data, self.server_addr)

    def start(self):
        if self.started:
            return
        self.started = True

        def client_read_thread():
            self.s = s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(0.5)

            logger.info("UDP client started on %s:%d", *self.server_addr)

            while self.started:
                while self.state == 0:
                    try:
                        self.write(HelloD2HPacket().encode())

                        in_raw, _ = s.recvfrom(2048)
                        self.read(in_raw) # Data Patch
                        in_raw, _ = s.recvfrom(2048)
                        self.read(in_raw) # Device Identify

                        s.settimeout(None)
                    except:
                        logger.warning("Error in UDP client hello")
                        pass

                try:
                    in_raw, _ = s.recvfrom(2048)
                    self.read(in_raw)
                except IndexError:
                    logger.error("Error in \"%s\" read thread, wrong state %d" % (self.name, self.state))
                except:
                    print("error buffer", in_raw)
                    logger.error("Error in \"%s\" read thread" % self.name, exc_info=True)

        def client_sync_thread():
            while self.started:
                with gb.sync_condition:
                    gb.sync_condition.wait()
                self._sync()


        threading.Thread(target=client_read_thread).start()
        threading.Thread(target=client_sync_thread).start()