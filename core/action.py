import threading
import time

def run(method):
    threading.Thread(target = method).start()

def wait(ms):
    time.sleep(ms / 1000)