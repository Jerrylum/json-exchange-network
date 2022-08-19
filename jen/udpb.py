import socket

from .gateway import *


class UDPBroadcast(Gateway):

    def __init__(self, addr: Address, listen=True):
        Gateway.__init__(self)

        self.s: socket.socket = None
        self.network_address: Address = addr
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
                    in_raw, addr = s.recvfrom(consts.PACKET_MAXIMUM_SIZE)

                    packet_id, data = PacketEncoder.unpack(in_raw)

                    available_packets = [MarshalDiffBroadcastPacket]
                    packet_class = [p for p in available_packets if p.PACKET_ID == packet_id][0]

                    packet = packet_class().decode(data)

                    if packet_class is MarshalDiffBroadcastPacket:
                        if any(packet.diff_id == d.diff_id for d in gb.diff_queue):
                            continue

                        gb.write(packet.path, packet.change, False, self)

                except BaseException:
                    print("error buffer", in_raw)
                    logger.error("Error in broadcast read thread", exc_info=True)

        if self.listen:
            threading.Thread(target=read_thread).start()
        threading.Thread(target=self._sync_thread).start()

    def _sync_exact_match(self, diff: Diff, packet: Packet, early: bool = False):
        if early:
            self.ignored_diff_id.add(diff.diff_id)
        elif diff.diff_id in self.ignored_diff_id:
            self.ignored_diff_id.remove(diff.diff_id)
            return

        self.write(packet)

    def write(self, packet: MarshalDiffBroadcastPacket):
        self.s.sendto(packet.data, ("<broadcast>", 7986))
