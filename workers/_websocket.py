import asyncio
import websockets
import time
import sys

from consts import *
from core.opcontrol import *
from core.protocol import *
from core.tools import *

import globals as gb

all_connections = []


class WebsocketConnection(RemoteDevice):
    manager: any
    ws: any
    event_loop: asyncio.AbstractEventLoop
    start_at: float
    init: bool

    write_lock = threading.Lock()

    def __init__(self, ws: any, manager: any):
        super().__init__(str(ws.id))
        self.manager = manager
        self.start_at = time.perf_counter()
        self.init = False
        self.ws = ws
        self.event_loop = asyncio.get_event_loop()
        gb.write("conn." + self.name, {"available": False, "type": "serial", "watch": []})
        self.open = True

    async def connection_job(self):
        try:
            time.sleep(0.5)

            self.write(GatewayIdentityU2DPacket().encode(self.name))
            gb.write("conn." + self.name + ".available", True)
            self.manager.update_device_info()
            self.init = True
            logger.info("Websocket device %s initialized" % self.name)

            while self.open:
                self.read(await self.ws.recv())

        except:
            logger.error("Error in \"%s\" read thread" % self.name, exc_info=True)
            self.manager.disconnect(self.name)

    async def _close(self):
        self.open = False
        await self.ws.close()
        gb.write("conn." + self.name, {"available": False, "type": "serial", "watch": []})


    def close(self):
        asyncio.run_coroutine_threadsafe(self._close(), loop=self.event_loop)

    def watch_update(self, path: str, val):
        self.write(DataPatchH2DPacket().encode(path, val))

    async def _write(self, packet: DownstreamBoundPacket):
        # print("send bytes", packet.data + bytes([0]))
        with self.write_lock:
            await self.ws.send(packet.data)

    def write(self, packet: DownstreamBoundPacket):
        asyncio.run_coroutine_threadsafe(self._write(packet), loop=self.event_loop)

    def read(self, buf: bytes):
        try:
            packet_id, data = unpack(buf)

            packet_class = [p for p in [DataPatchD2HPacket, DebugMessageD2UPacket] if p.PACKET_ID == packet_id][0]

            packet = packet_class().decode(data)

            if packet_class is DataPatchD2HPacket:
                old_watchers = False

                if packet.path == "conn." + self.name + ".watch":
                    old_watchers = gb.read(packet.path) or []

                # print("received size", len(buf))
                # print("change", packet.path, packet.receive)
                gb.write(packet.path, packet.receive)

                if old_watchers is not False:
                    diff_watchers = set(gb.read(packet.path)) - set(old_watchers)
                    for watcher in diff_watchers:
                        self.write(DataPatchH2DPacket().encode(watcher, gb.read(watcher)))
                    
                    self.manager.update_device_info()

            if packet_class is DebugMessageD2UPacket:
                # print("f", time.perf_counter())
                print("Website: {}".format(packet.message))  # TODO

        except BaseException:
            print("error buffer", buf)
            logger.error("Error in \"%s\" read thread" % self.name, exc_info=True)


class WebsocketConnectionManager:
    _worker: WorkerController

    address = "0.0.0.0"
    port = 8765
    started = False

    ignored_update = set()
    last_device_info = {}
    last_handled_diff = 0

    def __init__(self, worker: WorkerController):
        self._worker = worker

    def update_device_info(self):
        self.last_device_info = {k: v for k, v in dict(gb.read("device")).items()
                                 if k in self._worker._devices and type(self._worker._devices[k]) is WebsocketConnection}

    def connect(self):
        pass

    def disconnect(self, name: str):
        if name in self._worker._devices and type(self._worker._devices[name]) is WebsocketConnection:
            self._worker._devices[name].close()
            del self._worker._devices[name]
            self.update_device_info()
            logger.warning("Websocket device %s disconnected" % name)

    def start_listening(self):
        if self.started:
            return
        self.started = True

        def sync_thread():
            condition: threading.Condition = gb.share['__diff_condition__']
            while True:
                with condition:
                    condition.wait()
                    self.sync()

        threading.Thread(target=sync_thread).start()

        def main_thread():
            async def main():
                async with websockets.serve(self._connection_handler, self.address, self.port):
                    await asyncio.Future()  # run forever
            asyncio.run(main())

        threading.Thread(target=main_thread).start()

    def spin(self):
        pass

    def sync(self):
        all_diffs = gb.share["__diff__"]

        diffs = []
        last_handled = None
        for i in range(DIFF_QUEUE_SIZE, 0, -1): # XXX: ignore race condition
            diff = all_diffs[i - 1]
            if diff["uuid"] == self.last_handled_diff or diff["uuid"] == 0:
                break
            if last_handled is None:
                last_handled = diff["uuid"]
            if diff["uuid"] in self.ignored_update:
                self.ignored_update.remove(diff["uuid"])
                continue
            diffs.insert(0, diff)

        if last_handled is not None:
            self.last_handled_diff = last_handled

        # ~1ms passed

        cache = {}

        for diff in diffs:
            path = diff["path"]
            for device_name, device_info in self.last_device_info.items():
                for watcher in device_info["watch"]:
                    if watcher == "." or path == watcher:
                        watcher = path
                    elif path.startswith(watcher) or watcher.startswith(path):
                        pass
                    else:
                        continue

                    if watcher not in cache:
                        cache[watcher] = gb.read(watcher)
                    self._worker._devices[device_name].watch_update(watcher, cache[watcher])


    async def _connection_handler(self, ws):
        conn = WebsocketConnection(ws, self)
        self._worker._devices[conn.name] = conn
        self.update_device_info()
        logger.info("Websocket device %s connected" % conn.name)

        await conn.connection_job()


def run(worker: WorkerController):
    worker.init()

    manager = WebsocketConnectionManager(worker)
    manager.start_listening()

    while True:
        time.sleep(1)

    # asyncio.run(main())
