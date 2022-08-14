#!/bin/python3

import sys
sys.path.insert(1, './')

from jen import *

client = gb.connect_server(("127.0.0.1", 7984))
client.write(DiffPacket().encode("stop", True))

os._exit(0)
