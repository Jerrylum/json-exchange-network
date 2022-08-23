#!/bin/python3

import sys
sys.path.insert(1, './')

from jen import *


gb.init("initial.yml")
gb.start_gateway(UDPBroadcast("255.255.255.255", 7986))

try:
    while True:
        time.sleep(1)
        print(gb.read("counter"))
finally:
    os._exit(0)
