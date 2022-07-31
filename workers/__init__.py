# https://stackoverflow.com/questions/1057431/how-to-load-all-modules-in-a-folder

import os
for module in os.listdir(os.path.dirname(__file__)):
    if module == '__init__.py' or module[-3:] != '.py' or module.startswith('_') or module.count('.') > 1:
        continue
    __import__(__name__ + '.' + module[:-3], locals(), globals())
del module