
## Latency

Proccess to proccess latency 0.6ms to 0.8ms

## Protocol

### Packet

TODO

### Normal Mode

```
Client > Hello
Server > Data Patch ( All Data )
Server > Device Identify
Client > Data Patch ( Gateway information )
...
```

### Passive Mode

```
Server > Device Identify
Client > Data Patch ( Gateway information )
...
```

## Requirement

Used packages / libraries:
```
In Python
using: crc8, cobs, msgpack-python, websockets

In Arduino
due_can, Task Scheduler (by Kai Liebich & Georg Icking-Konert), hideakitai/MsgPack, hideakitai/Packetizer, ArduinoJson, ArxContainer
```


Included path in VS Code:
```
/home/cityurbc/Arduino/libraries/due_can
/home/cityurbc/Arduino/libraries/Task_Scheduler/src
/home/cityurbc/Arduino/libraries/MsgPack
/home/cityurbc/Arduino/libraries/ArduinoJson/src
/home/cityurbc/Arduino/libraries/ArxContainer
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