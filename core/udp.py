import uuid
import socket
import threading
import time
import uuid

import consts

from core.protocol import *
from core.tools import *
from core.gateway import *


class UDPConnection(UpstreamRole):

    def __init__(self, addr: Address, server: any):
        UpstreamRole.__init__(self)

        self.watching = set()

        self.conn_id = "UDP-" + str(uuid.uuid4())[:8]
        self.addr = addr
        self.server = server

    def write(self, packet: Packet):
        self.server.s.sendto(packet.data, self.addr)


class UDPServer(ServerLikeRole, Gateway):

    def __init__(self, addr: Address):
        ServerLikeRole.__init__(self)
        Gateway.__init__(self)

        self.s: socket.socket = None
        self.server_addr: Address = addr

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

        threading.Thread(target=server_thread).start()
        threading.Thread(target=self._sync_thread).start()


class UDPClient(DownstreamRole, Gateway):

    def __init__(self, addr: Address):
        DownstreamRole.__init__(self)
        Gateway.__init__(self)

        self.s: socket.socket = None

        self.server_addr = addr  

    def write(self, packet: Packet):
        self.s.sendto(packet.data, self.server_addr)

    def start(self):
        if self.started:
            return
        self.started = True
        
        self.s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.s.settimeout(0.5)

        def client_read_thread():
            logger.info("UDP client started")

            last_hello_attempt = 0

            while self.started:
                try:
                    if self.state == 0 and time.perf_counter() - last_hello_attempt > 0.5:
                        last_hello_attempt = time.perf_counter()
                        self.write(HelloD2UPacket().encode())

                    in_raw, _ = self.s.recvfrom(2048)
                    self.read(in_raw)
                except (TimeoutError, socket.timeout):
                    logger.warning("UDP client time out")
                except:
                    print("error buffer", in_raw)
                    logger.error("Error in \"%s\" read thread" % self.conn_id, exc_info=True)
                    self.state = 0

        threading.Thread(target=client_read_thread).start()
        threading.Thread(target=self._sync_thread).start()
