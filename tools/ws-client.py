import sys
sys.path.insert(1, './')

from jen import *


if __name__ == '__main__':
    gb.init("initial.yml")
    gb.connect_websocket_server(("127.0.0.1", 7985))

    try:
        while True:
            time.sleep(1)
    finally:
        os._exit(0)
