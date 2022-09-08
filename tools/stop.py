#!/bin/python3

import sys
sys.path.insert(1, './')

from jen import *

b = gb.start_gateway(UDPBroadcast("255.255.255.255", 7986))
gb.early_gateways.append(b)
gb.write("stop", True)

os._exit(0)
