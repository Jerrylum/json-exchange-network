#!/bin/python3

import sys
sys.path.insert(1, './')

from jen import *


gb.init("initial.yml")
gb.start_gateway(UDPBroadcast("255.255.255.255", 7986))

i = 0

try:
    while True:
        time.sleep(0.1)
        gb.write("counter", i)
        i += 1
finally:
    os._exit(0)
