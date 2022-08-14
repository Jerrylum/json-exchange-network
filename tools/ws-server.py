#!/bin/python3

import sys
sys.path.insert(1, './')

from jen import *


gb.init("initial.yml")
gb.create_websocket_server(("0.0.0.0", 7985))

try:
    while True:
        time.sleep(1)
        print(gb.read('conn'))
finally:
    os._exit(0)
