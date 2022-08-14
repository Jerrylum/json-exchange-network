#!/bin/python3

import sys
sys.path.insert(1, './')

from jen import *


gb.init("initial.yml")
gb.connect_websocket_server(("127.0.0.1", 7985))

try:
    while True:
        time.sleep(1)
finally:
    os._exit(0)
