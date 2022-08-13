## Overview

The Json Exchange Network is a middleware protocol and API standard that offers data distribution services. It is a decentralized network that allows JSON data to be exchanged between betweens processes and embedded systems. JEN is suitable for small robot prototypes.


## Json Exchange Network

Our team is facing a serious problem. It is a problem that, without clear and deliberate action, we will eventually come to a standstill. As the game's requirements become more complex, the complexity of the robot rises along with team competition. A simple robot with a joystick is no longer enough for the competition.

Therefore, the challenges we face every day will continue to escalate along with them. However, as the lab is only open until 5 pm on weekdays, while labs at other universities usually open 7 x 24, our time is limited. The situation is simple to understand but difficult to resolve—the reality is that there is no way we can solve this situation in the short term. But, we can try to use the limited resources as much as possible by improving the process of robot production. In the past, we had no way to build various robot components separately and perform unit testing. Every time we changed parameters in the code, we needed to re-upload the program again. Apart from that, the compilation speed was very slow, and the code was messy... For various reasons, we wasted a lot of time.

Json Exchange Network exists to improve the way we make robots. JEN is a middleware protocol and API standard that offers data distribution services. In ROS2, messages are exchanged using topics. All publishers and subscribers must use the same payload data format for each topic. In contrast, JEN uses nested paths and data in JSON format to provide a scalable architecture for data transfer. It allows us to build prototypes quickly, increase development speed, and reduce component-based development costs.

JEN was not built to replace ROS2; in fact, we can use JEN simultaneously with ROS2. We use JEN as the glue that holds the components together because a core that is simple and easy to maintain can bring convenience and save time. On the other hand, ROS2 can be used inside a component in a more complex situation.


## General Definitions

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", SHALL NOT", "SHOULD", "SHOULD NOT", "RECOMMENDED", "MAY", and "OPTIONAL" in this document are to be interpreted as described in RFC 2119.

**Connection:** An edge between two nodes, it can be either physical or logical.

**Diff:** The difference between the current version and the previous version of the document.

**Early Gateway:** A gateway that requires synchronization immediately after each `write` operation.

**Gateway:** A program that receives data updates from other node(s) and transmits updates from this node to other node(s). A node can have multiple gateways. A gateway MUST be one of the following roles:
    
- **Client-Like:** A role that is responsible for communicating with another node. It MUST be either upstream or downstream.

- **Server-Like:** A role that is responsible for communicating with multiple nodes.

**Naive Implementation:** A type of node implementation. A naive node does not track the Json document.

**Node:** A physical device, process or program from other computer that is connected to the network.

**Path:** A string that represents the location of a field in the Json document.

**Sync:** The synchronization of the data between nodes by a gateway.

**Watching Path** A set of paths that are watched by the downstream.

**Wildcard Path:** A path that ends with a wildcard character (`*`). 

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

For example, in the following graph, yellow, red, and blue represent a UDP, Serial and WebSockets connection respectively.

Nodes are communicating with each other via gateways (small circles).

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
This packet is sent by the downstream node to indicate that it is ready.

```
        ┌──────┐
Payload:│ \x00 │
        └──────┘
          Byte
```


#### 0x02 U2D Gateway Identity Packet
This packet is sent by the upstream when the downstream sends a "Hello" packet or when the connection is established in "Passive" mode.

The connection ID is a random string generated by the upstream to identify the downstream. 

```
        ┌─────────────┐
Payload:│Connection ID│
        └─────────────┘
           Var NTBS
```

#### 0x03 Diff Packet
A packet for both upstream and downstream. This packet is used to send the data changes to the network.

```
        ┌────────┬───────────────────────┐
Payload:│  Path  │MsgPack Serialized Data│
        └────────┴───────────────────────┘
         Var NTBS       Byte Array
```

#### 0x04 D2U Debug Message Packet
This packet is used to send debug messages to the upstream. Nodes like Arduino is using this packet to print messages in the console.

```
        ┌─────────┐
Payload:│ Message │
        └─────────┘
         Var NTBS
```

#### 0x05 Marshal Diff Packet
A packet for both upstream and downstream. This packet is used to send the data changes to the network just like the "Diff" packet. The difference is that this packet is using Marshal to serialize the data, which is faster than MsgPack in Python. This packet is used for the node to send the data changes between python nodes.

```
        ┌────────┬───────────────────────┐
Payload:│  Path  │Marshal Serialized Data│
        └────────┴───────────────────────┘
         Var NTBS       Byte Array
```


### Establishing a Connection

A connection can be established by the following actions:

- Data received from a new address and port pair in UDP server
- A Serial port is available
- A WebSocket connection is established


### Registering

After the connection is established, the connection is in the `Registering` state. Symbols `D` and `S` are used to represent `Downstream` and `Upstream`. The register process is as follows:

#### Normal Mode

```
D -> U: Hello
U -> D: Gateway Identity
D -> U: Data Patch with gateway information
        conn.<conn_id> = {available: true, type: "<type>", watch: <set of watching paths>}
```

#### Passive Mode

Passive mode is currently used in Serial connection. The host (computer) is the upstream and the device (Arduino / ESP32) is the downstream.

```
U -> D: Gateway Identity
D -> U: Data Patch with gateway information
        conn.<conn_id> = {available: true, type: "<type>", watch: <set of watching paths>}
...
```

### Running

A connection is in the `Running` state after the downstream sent any packets except `Hello`. The downstream could skip the `Registering` state if the downstream does not send a `Hello`. However, It is NOT RECOMMENDED.

A gateway is REQUIRED to broadcast data patches from the local diff queue to the network and receive data patches from the network to the local diff queue.

An upstream MUST only send the data patches watched by the downstream. However, a downstream MAY send any data patches to the upstream.

A set of watching paths is located in the `conn.<conn_id>.watch` field. An upstream can only send a data patch to a downstream if the path of the data patch fulfills any of the following conditions:
 - There is a wildcard path in the set that is a prefix of the path. For example, `foo.*` matches `foo.bar` and `foo.bar.baz` but not `foo`. The wildcard path `*` matches all paths.
 - There is a path in the set that is exactly the same


### Updating the Watching Paths

When the downstream updates its watching paths, the upstream MUST send data on all paths that are newly added to the set. Here is a pseudo-code for updating the watching paths:

```
if watching paths set is updated:

    update the Json document

    for path in (new set - old set):
        if path is not a wildcard path:
            send patch packet with the data on the path
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