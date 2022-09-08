import serial
import serial.tools.list_ports

from .gateway import *
from serial.tools.list_ports_common import ListPortInfo


class PortInfo:
    device: str = None
    vid: str = None
    pid: str = None
    serial_number: str = None

    baudrate: int = None

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    def match(self, other: ListPortInfo):
        for key in self.__dict__:
            if key == "baudrate":
                continue
            if key not in other.__dict__:
                return False
            if self.__dict__[key] != other.__dict__[key]:
                return False
        return True


class SerialConnection(UpstreamRole, Gateway):

    def __init__(self, path: str, baudrate: int, manager: any):
        UpstreamRole.__init__(self)
        Gateway.__init__(self)

        self.conn_id = "TTY-" + str(uuid.uuid4())[:8]
        self.device_path = path
        self.device_baudrate = baudrate
        self.manager = manager
        self.watching = set()
        self.diff_packet_type = DiffPacket

    def write(self, packet: Packet):
        try:
            with self.write_lock:
                self.s.write(packet.data + bytes([0]))
        except:
            logger.error("Error in \"%s\" write call" % self.conn_id, exc_info=True)
            self.manager.disconnect(self)

    def start(self):
        if self.started:
            return
        self.started = True

        self.s = serial.Serial(port=self.device_path, baudrate=self.device_baudrate)
        self.write_lock = threading.Lock()
        self.serial_rx = [0] * consts.PACKET_MAXIMUM_SIZE
        self.serial_rx_index = 0

        # Passive Mode

        def read_thread():
            try:
                time.sleep(consts.SERIAL_FIRST_PACKET_TIME_DELAY)

                # IMPORTANT: Clear the buffer before reading
                while self.s.inWaiting() > 0:
                    buf = self.s.read(self.s.inWaiting())

                logger.info("Send Identity to \"%s\" gateway" % self.conn_id)

                self.write(GatewayIdentityU2DPacket().encode(self.conn_id))

                while self.started:
                    buf = int(self.s.read(1)[0])
                    self.serial_rx[self.serial_rx_index] = buf
                    self.serial_rx_index += 1

                    if buf == 0:  # Delimiter byte
                        try:
                            in_raw = bytes(self.serial_rx[:self.serial_rx_index])
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

    def stop(self):
        Gateway.stop(self)
        self.s.close()


class SerialConnectionManager(GatewayManager):

    def __init__(self, worker: WorkerController):
        self._worker = worker

        self.whitelist: list[PortInfo] = []

        self.last_connect_attempt = 0
        self.using_devices = []

    def connect(self):
        tty_list = [p for p in list(serial.tools.list_ports.comports()) if p.device not in consts.PORT_BLACKLIST]

        tty_list = [p for p in tty_list if any(w.match(p) for w in self.whitelist)]

        for f in tty_list:
            if f.device in self.using_devices:
                continue

            try:
                info = next(w for w in self.whitelist if w.match(f))
                conn = SerialConnection(f.device, info.baudrate, self)
                conn.start()
                self.using_devices.append(f.device)
                gb.gateways.append(conn)
                gb.early_gateways.append(conn)
                logger.info("Serial connection %s (%s) is established" % (f.device, f.serial_number))
            except:
                logger.warning("Unable to establish serial connection %s" % f.device)

    def disconnect(self, conn: SerialConnection):
        if conn.device_path in self.using_devices:
            conn.stop()
            self.using_devices.remove(conn.device_path)
            gb.gateways.remove(conn)
            gb.early_gateways.remove(conn)
            gb.write("conn." + conn.conn_id, None)
        logger.warning("Serial connection %s is closed" % conn.device_path)

    def spin(self):
        if time.perf_counter() - self.last_connect_attempt > consts.CONNECTION_RETRY_DELAY:
            self.last_connect_attempt = time.perf_counter()
            self.connect()
