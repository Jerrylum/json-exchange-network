import time

import globals as gb


def run(share):
    gb.share = share

    while True:
        time.sleep(1)
        # print(gb.read('process'), end='       \r')
