## Interpretation

**Network:** A distributed database dedicated to storing and retrieving JSON data.

**Node:** A physical device, process or program from other computer that is connected to the network.

**Connection:** An edge between two nodes, it can be either physical or logical.

**Gateway:** A portal to the network, it is a role in every node that is responsible for routing patch messages to other nodes and receiving them from other nodes. A node can have multiple gateways.

**Server-Like Gateway:** A role that is responsible for routing patch messages to various connections.

**Client-Like Gateway:** A role that is responsible for sending patch messages to the other end.


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
(when client updates watcher list)
Server > Data Patch ( Watching Data )
```

## Requirement

Used packages / libraries:
```
In Python
using: crc8, cobs, msgpack, websockets

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