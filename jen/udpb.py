import socket

from .gateway import *


class UDPBroadcast(Gateway, PacketOrigin):

    def __init__(self, ip: str, port: int, listen=True):
        Gateway.__init__(self)

        self.s: socket.socket = None
        self.network_address: Address = (ip, port)
        self.diff_packet_type = MarshalDiffBroadcastPacket
        self.listen = listen

    def start(self):
        if self.started:
            return
        self.started = True

        self.s = s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR if os.name == "nt" else socket.SO_REUSEPORT, 1)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        s.bind(("", self.network_address[1]) if os.name == "nt" else self.network_address)

        def read_thread():
            logger.info("UDP broadcast started on %s:%d", *self.network_address)

            while self.started:
                try:
                    in_raw = None
                    in_raw, addr = s.recvfrom(consts.PACKET_MAXIMUM_SIZE)

                    self.read(in_raw)
                except BaseException:
                    if self.s is None:
                        logger.info("Server read thread closed")
                    else:
                        print("error buffer", in_raw)
                        logger.error("Error in broadcast read thread", exc_info=True)

        if self.listen:
            threading.Thread(target=read_thread).start()
        threading.Thread(target=self._sync_thread).start()

    def _sync_exact_match(self, diff: Diff, packet: Packet, early: bool = False):
        if early:
            self.ignored_diff_id.add(diff.diff_id)

        self.write(packet)

    def read(self, in_raw: bytes):
        packet = self._decode_packet(in_raw, [MarshalDiffBroadcastPacket])
        packet_class = type(packet)

        if packet_class is MarshalDiffBroadcastPacket:
            if any(packet.diff_id == d.diff_id for d in gb.diff_queue):
                return

            gb.write(packet.path, packet.change, False, self)

    def write(self, packet: MarshalDiffBroadcastPacket):
        self.s.sendto(packet.data, ("<broadcast>", self.network_address[1]))

    def stop(self):
        Gateway.stop(self)
        if self.s is not None:
            try:
                self.s.shutdown(socket.SHUT_RDWR)
            except:
                pass
            self.s = None
