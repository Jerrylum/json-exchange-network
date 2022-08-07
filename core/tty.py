import serial
import serial.tools.list_ports
import time
import threading
import os

import consts

from core.protocol import *
from core.tools import *
from core.gateway import *
from serial.tools.list_ports_common import ListPortInfo

import globals as gb

class PortInfo:
    device: str = None
    vid: str = None
    pid: str = None
    serial_number: str = None

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    def match(self, other: ListPortInfo):
        for key in self.__dict__:
            if key not in other.__dict__:
                return False
            if self.__dict__[key] != other.__dict__[key]:
                return False
        return True


class SerialConnection(GatewayClientLike, Gateway):

    def __init__(self, path: str, manager: any):
        GatewayClientLike.__init__(self)
        Gateway.__init__(self)

        self.conn_id = str(uuid.uuid4())[:8]
        self.device_path = path
        self.manager = manager
        self.diff_packet_type = DiffPacket

    def read(self, in_raw: bytes):
        packet_id, data = unpack(in_raw)

        packet_class = [p for p in [DiffPacket, DebugMessageC2SPacket] if p.PACKET_ID == packet_id][0]

        packet = packet_class().decode(data)

        if packet_class is DiffPacket:
            if ("conn." + self.conn_id + ".watch").startswith(packet.path):
                watcher_path = "conn." + self.conn_id + ".watch"
                old_watchers = gb.read(watcher_path) or []

                gb.write(packet.path, packet.change)

                self.watching = gb.read(watcher_path) or []
                diff_watchers = set(self.watching) - set(old_watchers)
                for watcher in diff_watchers:
                    self.write(DiffPacket().encode(watcher, gb.read(watcher)))
            else:
                gb.write(packet.path, packet.change)
        elif packet_class is DebugMessageC2SPacket:
            # print("Arduino: {} {}".format(packet.message, time.perf_counter()))  # TODO
            logger.debug("Receive: %f" % time.perf_counter())
            # print("Arduino: {}".format(packet.message))  # TODO

        if self.state == 0:
            self.state = 1
            logger.info("Gateway \"%s\" registered" % self.conn_id)

    def write(self, packet: Packet):
        with self.write_lock:
            self.s.write(packet.data + bytes([0]))

    def start(self):
        self.start_at = time.perf_counter()
        self.s = serial.Serial(port=self.device_path, baudrate=115200)
        self.write_lock = threading.Lock()
        self.serial_rx = [0] * 2048
        self.serial_rx_index = 0

        self.started = True

        # Passive Mode

        def read_thread():
            try:
                time.sleep(consts.SERIAL_FIRST_PACKET_TIME_DELAY)

                # IMPORTANT: Clear the buffer before reading
                while self.s.inWaiting() > 0:
                    buf = self.s.read(self.s.inWaiting())

                logger.info("Send Identity to \"%s\" gateway" % self.conn_id)

                self.write(GatewayIdentityC2SPacket().encode(self.conn_id))

                while self.started:
                    buf = int(self.s.read(1)[0])
                    self.serial_rx[self.serial_rx_index] = buf
                    self.serial_rx_index += 1

                    if buf == 0:
                        try:
                            in_raw = bytes(self.serial_rx[0: self.serial_rx_index])
                            self.read(in_raw)
                        except BaseException:
                            print("error buffer", in_raw)
                            logger.error("Error in server read thread", exc_info=True)
                        self.serial_rx_index = 0
            except:
                logger.error("Error in \"%s\" read thread" % self.conn_id, exc_info=True)
                self.manager.disconnect(self)

        threading.Thread(target=read_thread).start()
        threading.Thread(target=self._sync_thread).start()


class SerialConnectionManager(GatewayManager):

    def __init__(self, worker: WorkerController):
        self._worker = worker

        self.whitelist: list[PortInfo] = []

        self.last_connect_attempt = 0
        self.using_device = []

    def try_change_port_permission(self, path: str):
        try:
            os.system("echo %s|sudo -S %s" % ("robocon", "chmod 666 " + path))
            print("sudo chmod port", path)
        except:
            print("Unable to chmod port", path)

    def connect(self):
        self.last_connect_attempt = time.perf_counter()

        tty_list = [p for p in list(serial.tools.list_ports.comports()) if p.device not in consts.PORT_BLACKLIST]

        tty_list = [p for p in tty_list if any(w.match(p) for w in self.whitelist)]

        for f in tty_list:
            if f.device in self.using_device:
                continue

            try:
                conn = SerialConnection(f.device, self)
                conn.start()
                self.using_device.append(f.device)
                gb.gateways.append(conn)
                gb.early_gateways.append(conn)
                logger.info("Serial connection %s (%s) is established" % (f.device, f.serial_number))
            except:
                self.try_change_port_permission(f)

    def disconnect(self, conn: SerialConnection):
        self.using_device.remove(conn.device_path)
        gb.gateways.remove(conn)
        gb.early_gateways.remove(conn)
        logger.warning("Serial connection %s is closed" % conn.device_path)

    def spin(self):
        if time.perf_counter() - self.last_connect_attempt > 1:
            self.connect()

