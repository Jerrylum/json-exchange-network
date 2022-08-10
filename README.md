## Overview

The Json Exchange Network is a middleware protocol and API standard that offers data distribution services. It is a decentralized network that allows JSON data to be exchanged between betweens processes and embedded systems. JEN is suitable for small robot prototypes.


## Json Exchange Network

Our team is facing a serious problem. It is a problem that, without clear and deliberate action, we will eventually come to a standstill. As the game's requirements become more complex, the complexity of the robot rises along with team competition. A simple robot with a joystick is no longer enough for the competition.

Therefore, the challenges we face every day will continue to escalate along with them. However, as the lab is only open until 5 pm on weekdays, while labs at other universities usually open 7 x 24, our time is limited. The situation is simple to understand but difficult to resolve—the reality is that there is no way we can solve this situation in the short term. But, we can try to use the limited resources as much as possible by improving the process of robot production. In the past, we had no way to build various robot components separately and perform unit testing. Every time we changed parameters in the code, we needed to re-upload the program again. Apart from that, the compilation speed was very slow, and the code was messy... For various reasons, we wasted a lot of time.

Json Exchange Network exists to improve the way we make robots. JEN is a middleware protocol and API standard that offers data distribution services. In ROS2, messages are exchanged using topics. All publishers and subscribers must use the same payload data format for each topic. In contrast, JEN uses nested paths and data in JSON format to provide a scalable architecture for data transfer. It allows us to build prototypes quickly, increase development speed, and reduce component-based development costs.

JEN was not built to replace ROS2; in fact, we can use JEN simultaneously with ROS2. We use JEN as the glue that holds the components together because a core that is simple and easy to maintain can bring convenience and save time. On the other hand, ROS2 can be used inside a component in a more complex situation.


## General Definitions

**Connection:** An edge between two nodes, it can be either physical or logical.

**Diff:** The difference between the current version and the previous version of the document

**Early Gateway:** A gateway that requires synchronization immediately after each `write` operation.

**Gateway:** A program that receives data updates from other node(s) and transmits updates from this node to other node(s). A node can have multiple gateways. A gateway must be one of the following roles:
    
- **Client-Like:** A role that is responsible for communicating with another node. It can be either upstream or downstream.

- **Server-Like:** A role that is responsible for communicating with multiple nodes.

**Node:** A physical device, process or program from other computer that is connected to the network.

**Sync:** The synchronization of the data between the nodes by a gateway.

**Watching Path** A set of diff paths that a gateway will only accept.

## How It Works

Every node in the network keeps an identical Json document that stores the state of the robot, it might look like this:

```json
{
    "shooter": {
        "pid": {
            "p": 0.03,
            "i": 0.0,
            "d": 0.45
        },
        "target_speed": 4600,
        "now_speed": 4587.34
    },
    "opcontrol": {
        "joystick": {
            "axes": {
                "x": 0.0,
                ...
            },
            "btns": { ... }
        }
    },
    ...
}
```

When one of the nodes needs to update part of this document, instead of sending the whole document, it only send the difference between the current version and the previous version. For example:

```py
shooter.target_speed = 3700
```

Only the location and the updated value are broadcast to each node. As a result, the state of the robot can be synchronized to each node without wasting bandwidth to transmit the entire document.

Here is an example in the code:

```py
# Node A
gb.write("shooter.pid.p", 0.035)

# It is also possible to update multiple values at once
gb.write("shooter.pid", {"p": 0.03, "i": 0.0, "d": 0.45})

# Node B
gb.read("shooter.pid.p") # returns 0.035
```

![Network Graph](https://imgur.com/PO7P0NZ.png)

## Protocol

The Json Exchange Network accepts connections in UDP, Serial, and WebSockets by default. Each node communicates with other nodes using frames.

A packet is a sequence of bytes wrapped in a frame and sent to the other node. Consistent Overhead Byte Stuffing (COBS) is used to wrap the packet into a frame. It uses a specific byte value, zero, as a packet delimiter to indicate the boundary between packets, which makes it simple for receiving applications to recover from malformed packets.

### Protocol Definitions

**Data Types:** The following data types are used in the protocol.

|Name|Size (bytes)|Encodes|Notes|
|-|-|-|-|
|Byte          |1              |An integer between -128 and 127                 |Signed 8-bit integer, two's complement.|
|Unsigned Byte |1              |An integer between 0 and 255	                |Unsigned 8-bit integer.|
|Var NTBS (n)  |≥ 1<br/>≤ n + 1|A null-terminated byte string                   |Consist of a sequence of nonzero bytes then followed by a byte with value zero (the terminating null character).|
|CRC8          |1              |8 bits CRC integrity checksum                   ||
|Byte Array    |Varies         |Depends on context                              |A sequence of zero or more bytes.|

### Packet & Frame Format

Frames have no size limit. However, Arduino only accepts frames smaller than 1024 bytes.

Packet frames diagram:
```
       ┌──────┬─────────────┬────────┐
Packet:│ Type │Payload Bytes│Checksum├──┐
       └──────┴─────────────┴────────┘  │
        1 byte    M Bytes     1 byte    │
                                        ▼
       ┌────────┬───────────────────────────┬─────────┐
 Frame:│Overhead│  Transformed Packet Data  │Delimiter│
       └────────┴───────────────────────────┴─────────┘
         1 byte            N bytes            1 byte
```

Format:

- Type [Unsigned Byte]
- Payload Bytes [Byte Array]
- Checksum [CRC8]

#### 0x01 D2U Hello Packet
An upstream bound packet. This packet is used for the node to begin the handshake with the network in "Normal" mode.

```
        ┌──────┐
Payload:│ \x00 │
        └──────┘
          Byte
```


#### 0x02 U2D Gateway Identity Packet
A downstream bound packet. The connection ID is a random string generated by the upstream client to identify the downstream client. This package is sent after the upstream client has sent a "Hello" packet.

```
        ┌─────────────┐
Payload:│Connection ID│
        └─────────────┘
           Var NTBS
```

#### 0x03 Diff Packet
A packet for both upstream and downstream clients. This packet is used to send the data changes to the network.

```
        ┌────────┬───────────────────────┐
Payload:│  Path  │MsgPack Serialized Data│
        └────────┴───────────────────────┘
         Var NTBS       Byte Array
```

#### 0x04 D2U Debug Message Packet
An upstream bound packet. This packet is used for external nodes like Arduino to print messages in the console.

```
        ┌─────────┐
Payload:│ Message │
        └─────────┘
         Var NTBS
```


#### 0x05 Marshal Diff Packet
A packet for both upstream and downstream clients. This packet is used to send the data changes to the network just like the "Diff" packet. The difference is that this packet is using Marshal to serialize the data, which is faster than MsgPack in Python. This packet is used for the node to send the data changes between python nodes.

```
        ┌────────┬───────────────────────┐
Payload:│  Path  │Marshal Serialized Data│
        └────────┴───────────────────────┘
         Var NTBS       Byte Array
```


### Mechanism

#### Normal Mode

```
Downstream > Hello
Upstream   > Gateway Identity
Downstream > Data Patch ( Gateway information )
...
```

#### Passive Mode

```
Upstream   > Gateway Identity
Downstream > Data Patch ( Gateway information )
...
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