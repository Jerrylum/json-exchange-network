import asyncio
import websockets

from .gateway import *


class WebsocketConnection(UpstreamRole):

    def __init__(self, ws: any, server: any):
        UpstreamRole.__init__(self)

        self.watching = set()

        self.conn_id = "WS-" + str(uuid.uuid4())[:8]
        self.ws = ws
        self.server = server
        self.write_lock = threading.Lock()
        self.event_loop = asyncio.get_event_loop()

    async def _write(self, packet: Packet):
        with self.write_lock:
            await self.ws.send(packet.data)

    def write(self, packet: Packet):
        asyncio.run_coroutine_threadsafe(self._write(packet), loop=self.event_loop)
    

class WebsocketServer(ServerLikeRole, Gateway):

    def __init__(self, ip: str, port: int):
        ServerLikeRole.__init__(self)
        Gateway.__init__(self)

        self.s: any = None
        self.server_addr: Address = (ip, port)

        self.connections: dict[uuid.UUID, WebsocketConnection] = {}
        self.stop_event: threading.Event = None

    def start(self):
        if self.started:
            return
        self.started = True

        async def connection_handler(ws: any):
            conn = WebsocketConnection(ws, self)
            self.connections[ws.id] = conn

            logger.info("Websocket connection %s is established" % ws.id)

            try:
                while self.started:
                    conn.read(await conn.ws.recv())
            except websockets.exceptions.ConnectionClosed:
                pass
            except websockets.exceptions.ConnectionClosedOK:
                pass
            except:
                logger.error("Error in server read thread", exc_info=True)
            finally:
                del self.connections[ws.id]
                gb.write("conn." + conn.conn_id, None)
                logger.info("Websocket connection %s is closed" % ws.id)

        def main_thread():
            async def main():
                self.stop_event = threading.Event()
                stop = asyncio.get_event_loop().run_in_executor(None, self.stop_event.wait)

                async with websockets.serve(connection_handler, self.server_addr[0], self.server_addr[1]) as self.s:
                    await stop
            asyncio.run(main())

        threading.Thread(target=main_thread).start()
        threading.Thread(target=self._sync_thread).start()

    def stop(self):
        Gateway.stop(self)
        if self.s:
            self.stop_event.set()
            self.s = None
        

class WebsocketClient(DownstreamRole, Gateway):

    def __init__(self, ip: str, port: int):
        DownstreamRole.__init__(self)
        Gateway.__init__(self)

        self.s: any = None

        self.server_addr = (ip, port)
        self.write_lock = threading.Lock()
        self.event_loop: asyncio.AbstractEventLoop = None

    async def _write(self, packet: Packet):
        try:
            with self.write_lock:
                await self.s.send(packet.data)
        except:
            logger.error("Error in \"%s\" write call" % self.conn_id, exc_info=True)

    def write(self, packet: Packet):
        asyncio.run_coroutine_threadsafe(self._write(packet), loop=self.event_loop)

    def start(self):
        if self.started:
            return
        self.started = True

        def client_read_thread():
            async def client_job():
                logger.info("Websocket client started")

                self.event_loop = asyncio.get_event_loop()

                while self.started:
                    try:
                        async with websockets.connect("ws://%s:%d" % self.server_addr) as ws:
                            logger.info("Websocket connection %s is established" % ws.id)

                            self.s = ws
                            await self._write(HelloD2UPacket().encode())

                            while self.started:
                                self.read(await ws.recv())
                    except ConnectionRefusedError:
                        logger.warning("Websocket connection refused")
                    except websockets.exceptions.ConnectionClosedOK:
                        pass
                    except websockets.exceptions.ConnectionClosedError:
                        logger.warning("Websocket connection is closed unexpectedly")
                    except:
                        logger.error("Error in \"%s\" read thread" % self.conn_id, exc_info=True)
                    finally:
                        self.state = 0
                        time.sleep(consts.CONNECTION_RETRY_DELAY)
                        logger.warning("Websocket connection is closed")

            asyncio.run(client_job())

        threading.Thread(target=client_read_thread).start()
        threading.Thread(target=self._sync_thread).start()

    async def _stop(self):
        if self.s:
            await self.s.close()
            self.s = None

    def stop(self):
        Gateway.stop(self)
        asyncio.run_coroutine_threadsafe(self._stop(), loop=self.event_loop)
