# https://stackoverflow.com/questions/1057431/how-to-load-all-modules-in-a-folder

import os
for module in os.listdir(os.path.dirname(__file__)):
    if module == '__init__.py' or module[-3:] != '.py':
        continue
    __import__(__name__ + '.' + module[:-3], locals(), globals())
del module