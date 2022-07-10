
## JSON Structure

```json

// ASCII only
// never start with an underscore

// joystick
{
    "main": {
        "available": true,
        "update": 1656566710.9527078,
        "axes": {
            ...
        },
        "btns": {
            ...
        }
    }
}

// process
{
    "main": {
        "pid": 15301,
        "update": 1656566710.9527078
    },
    "subprocess": {
        "watchdog": {
            "is_alive": true,
            "pid": 15315
        },
        "joystick": {
            "is_alive": true,
            "pid": 15316
        }
    }
}

// robot
{
    "shooterx": {
        "target_pos": 0.0, // -->
        "now_pos": 0.0,    // <--
        "output": 0.0,     // <--
        "pid": {
            "max": 2000,
            "min": -2000,
            "p": 0.35,
            "d": 180,
            "i": 0
        }
    },
    "shootery": {
        "target_pos": 0.0,
        "now_pos": 0.0,
        "output": 0.0,
        "pid": {
            "max": 4000,
            "min": -4000,
            "p": 0.35,
            "d": 180,
            "i": 0
        }
    },
    "BLDC": false,
    "Elevator": false,
    "Pusher": false,
    "Platform": false
}

// serial
{
    "ttyACM0": {
        "available": true,
        "watch": [
            "robot.shooterx.target_pos"
        ]
    }    
}

// __diff__
[
    "robot.shooterx.target_pos",
    "robot.shooterx.now_pos"
]

```


## Requirement

Used packages / libraries:
```
In Python
using: crc8, cobs, msgpack-python

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