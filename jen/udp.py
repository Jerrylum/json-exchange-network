import socket

from .gateway import *


class UDPConnection(UpstreamRole):

    def __init__(self, addr: Address, server: any):
        UpstreamRole.__init__(self)

        self.watching = set()

        self.conn_id = "UDP-" + str(uuid.uuid4())[:8]
        self.addr = addr
        self.server = server

    def write(self, packet: Packet):
        self.server.s.sendto(packet.data, self.addr)

    def _sync_exact_match(self, diff: Diff, packet: Packet, early: bool = False):
        if self.state == 2:
            del self.server.connections[self.addr]
            return

        UpstreamRole._sync_exact_match(self, diff, packet, early)


class UDPServer(ServerLikeRole, Gateway):

    def __init__(self, ip: str, port: int):
        ServerLikeRole.__init__(self)
        Gateway.__init__(self)

        self.s: socket.socket = None
        self.server_addr: Address = (ip, port)

        self.connections: dict[Address, UDPConnection] = {}

    def start(self):
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
                    in_raw, addr = s.recvfrom(consts.PACKET_MAXIMUM_SIZE)

                    if addr not in self.connections:
                        self.connections[addr] = UDPConnection(addr, self)

                    self.connections[addr].read(in_raw)
                except BaseException:
                    if self.s is None:
                        logger.info("Server read thread closed")
                    else:
                        print("error buffer", in_raw)
                        logger.error("Error in server read thread", exc_info=True)

        threading.Thread(target=server_thread).start()
        threading.Thread(target=self._sync_thread).start()

    def stop(self):
        Gateway.stop(self)
        if self.s is not None:
            try:
                self.s.shutdown(socket.SHUT_RDWR)
            except:
                pass
            self.s = None



class UDPClient(DownstreamRole, Gateway):

    def __init__(self, ip: str, port: int):
        DownstreamRole.__init__(self)
        Gateway.__init__(self)

        self.s: socket.socket = None

        self.server_addr = (ip, port)

    def write(self, packet: Packet):
        self.s.sendto(packet.data, self.server_addr)

    def start(self):
        if self.started:
            return
        self.started = True

        self.s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.s.settimeout(consts.CONNECTION_TIMEOUT)

        def client_read_thread():
            logger.info("UDP client started")

            last_hello_attempt = 0

            while self.started:
                try:
                    if self.state == 0 and time.perf_counter() - last_hello_attempt > consts.CONNECTION_RETRY_DELAY:
                        last_hello_attempt = time.perf_counter()
                        self.write(HelloD2UPacket().encode())

                    in_raw = None
                    in_raw, _ = self.s.recvfrom(consts.PACKET_MAXIMUM_SIZE)
                    self.read(in_raw)
                except (TimeoutError, socket.timeout):
                    logger.warning("UDP client time out")
                    self.state = 0
                except:
                    print("error buffer", in_raw)
                    logger.error("Error in \"%s\" read thread" % self.conn_id, exc_info=True)
                    self.state = 0

        threading.Thread(target=client_read_thread).start()
        threading.Thread(target=self._sync_thread).start()

    def stop(self):
        Gateway.stop(self)
        if self.s is not None:
            try:
                self.s.shutdown(socket.SHUT_RDWR)
            except:
                pass
            self.s = None
