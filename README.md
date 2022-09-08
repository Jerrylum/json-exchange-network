## Overview

The Json Exchange Network is a middleware protocol and API standard that offers data distribution services. It is a decentralized network that allows JSON data to be exchanged between processes and embedded systems. JEN is suitable for small robot prototypes.


## Requirement

Used libraries in Arduino:
```
CAN (by Sandeep Mistry) # might not needed
due_can (by Collin Kidder and more)
esp32_can (https://github.com/collin80/esp32_can) # include manually on GUI
can_common (https://github.com/collin80/can_common) # include manually on GUI
Task Scheduler (by Kai Liebich & Georg Icking-Konert)
MsgPack (by hideakitai)
Packetizer (by hideakitai)
ArduinoJson (by Benoit Blanchon)
ArxContainer (by hideakitai)
ESP32Servo (by John K. Bennett,Kevin Harrington)
```


Included paths in VS Code:
```
/home/cityurbc/Arduino/libraries/due_can
/home/cityurbc/Arduino/libraries/esp32_can-master/src
/home/cityurbc/Arduino/libraries/can_common-master/src
/home/cityurbc/Arduino/libraries/Task_Scheduler/src
/home/cityurbc/Arduino/libraries/MsgPack
/home/cityurbc/Arduino/libraries/Packetizer
/home/cityurbc/Arduino/libraries/ArduinoJson/src
/home/cityurbc/Arduino/libraries/ArxContainer
/home/cityurbc/Arduino/libraries/ESP32Servo/src
```


Changed settings in VS Code:
```
C_Cpp.clang_format_fallbackStyle: { BasedOnStyle: Google, ColumnLimit: 120 }
C_Cpp.workspaceParsingPriority: low
python.formatting.autopep8Args: ["--max-line-length=120"]
```


Make sure you setup your git
```
git config --global user.name ""
git config --global user.email ""
```


Install pytest
```
pip3 install -U pytest
pip3 install pytest-cov

pytest --cov=jen --cov-report html:cov_html tests/
```
