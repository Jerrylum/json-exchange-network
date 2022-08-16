#!/bin/python3

import sys
sys.path.insert(1, './')

from jen import *


gb.init("initial.yml")
gb.connect_server(("127.0.0.1", 7984))

try:
    time.sleep(1)
    print(gb.read("conn"))
finally:
    os._exit(0)
