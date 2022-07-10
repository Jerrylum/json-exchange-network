import sys
sys.path.insert(1, './') # run the script on project root dirt

import os
import time
from multiprocessing import Manager, Process
from types import ModuleType
from typing import Dict

import globals as gb
import workers

def clearupAllPythonProcess():
    # kill but without yourself
    os.system('sudo kill $(pgrep -f "python3 main.py" | grep -v ' + str(os.getpid()) + ') &> /dev/null')

if __name__ == '__main__':
    # kill all process that start before it
    # clearupAllPythonProcess() # optional

    if 'DISPLAY' not in os.environ:
        os.environ['DISPLAY'] = ':0'

    try:
        gb.init(Manager(), ['joystick', 'process', 'robot', 'serial'])

        processes: Dict[str, Process] = {}

        for name in workers.__dict__:
            worker = workers.__dict__[name]
            if type(worker) is ModuleType and 'run' in worker.__dict__:
                p = Process(target=worker.run)
                p.start()
                processes[name] = p

        gb.write('process.main.pid', os.getpid())
        while True:
            gb.write('process.main.update', time.time())
            gb.write('process.subprocess', {
                name: {
                    'is_alive': processes[name].is_alive(),
                    'pid': processes[name].pid
                } for name in processes })
            time.sleep(0.2)

    except KeyboardInterrupt:
        print('Keyboard interrupt')

    [processes[name].kill() for name in processes]

    print('Program exit')

    exit()