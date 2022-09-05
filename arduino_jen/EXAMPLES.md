## Arduino Due Multitask with CAN-Bus Example (Tested with 2022-R1D2)

### Initial Data

```yml
rs: ## robot_shooter
  s: ## setting
    sx: ## shooter x
      pid:
        max: 2000
        min: -2000
        p: 0.35
        d: 180
        i: 0
    sy: ## shooter y
      pid:
        max: 4000
        min: -4000
        p: 0.35
        d: 180
        i: 0
  o: ## output
  - 0 ## shooter x target_pos
  - 0 ## shooter x target_pos
  f: ## feedback
  - 0 ## shooter x now_pos
  - 0 ## shooter x now_speed
  - 0 ## shooter x output_speed
  - 0 ## shooter y now_pos
  - 0 ## shooter y now_speed
  - 0 ## shooter y output_speed

rg: ## robot_general
  o:
  - false ## BLDC
  - false ## elevator
  - false ## pusher
  - false ## platform
  f:
  - 0 ## sensor1
  - 0 ## sensor2
```

### CPP Code

```cpp
#include <Tasks.h>
#include <due_can.h>

#define INO_FILE

#include "jen.hpp"

#include "pid.hpp"
#include "bounding_helper.hpp"
#include "rm_motor.hpp"

#define EN 6
#define AIR_PA 3
#define AIR_PB 2
#define AIR_EA 4
#define AIR_EB 5
#define AIR_PLATFORM_UP 7
#define AIR_PLATFORM_DOWN 8

CAN_FRAME tx_msg, rx_msg;

#define GROUP1_MOTOR_COUNT 2
RMM3508Motor group1_rm[GROUP1_MOTOR_COUNT] = {RMM3508Motor(0, POS_PID_MODE), RMM3508Motor(1, POS_PID_MODE)};

DECLARE_WATCHER(JsonObject, shooter_setting, "rs.s",
  JsonVariant sx = value["sx"]["pid"];
  JsonVariant sy = value["sy"]["pid"];

  PIDImpl* sx_pid = group1_rm[0].pos_pid;
  sx_pid->_max_val = sx["max"] | 0.0;
  sx_pid->_min_val = sx["min"] | 0.0;
  sx_pid->_Kp = sx["p"] | 0.0;
  sx_pid->_Kd = sx["d"] | 0.0;
  sx_pid->_Ki = sx["i"] | 0.0;

  PIDImpl* sy_pid = group1_rm[1].pos_pid;
  sy_pid->_max_val = sy["max"] | 0.0;
  sy_pid->_min_val = sy["min"] | 0.0;
  sy_pid->_Kp = sy["p"] | 0.0;
  sy_pid->_Kd = sy["d"] | 0.0;
  sy_pid->_Ki = sy["i"] | 0.0;

  static int count = 0;
  console << "updated pid" << count++ << "\n";
)

DECLARE_WATCHER(JsonArray, gen_output, "rg.o",
  bool BLDC = value[0].as<bool>();
  bool elevator = value[1].as<bool>();
  bool pusher = value[2].as<bool>();
  bool platform = value[3].as<bool>();

  digitalWrite(EN, BLDC ? HIGH : LOW);
  digitalWrite(AIR_EA, elevator ? LOW : HIGH);
  digitalWrite(AIR_EB, elevator ? HIGH : LOW);
  digitalWrite(AIR_PA, pusher ? LOW : HIGH);
  digitalWrite(AIR_PB, pusher ? HIGH : LOW);
  digitalWrite(AIR_PLATFORM_UP, platform ? LOW : HIGH);
  digitalWrite(AIR_PLATFORM_DOWN, platform ? HIGH : LOW);

  static int count = 0;
  // console << "updated " << count++ << "\n";
  console << count++ << "\n";
)

DECLARE_WATCHER(JsonArray, shooter_output, "rs.o",
  int x = value[0].as<int>();
  int y = value[1].as<int>();

  group1_rm[0].target_tick = x;
  group1_rm[1].target_tick = y;

  // static int count = 0;
  // console << "shooter updated " << count++ << "\n";
  // console << x << "\n";
)

void setup() {
  pinMode(LED_BUILTIN, OUTPUT);
  pinMode(EN, OUTPUT);
  pinMode(AIR_PA, OUTPUT);
  pinMode(AIR_EA, OUTPUT);
  pinMode(AIR_PB, OUTPUT);
  pinMode(AIR_EB, OUTPUT);
  pinMode(AIR_PLATFORM_UP, OUTPUT);
  pinMode(AIR_PLATFORM_DOWN, OUTPUT);

  START_WATCHER(shooter_setting);
  START_WATCHER(gen_output);
  START_WATCHER(shooter_output);

  Can0.begin(CAN_BPS_1000K);  //  For communication with RM motors

  gb.setup(115200);

  Tasks_Add((Task)loop1, 1, 0);
  Tasks_Add((Task)loop2, 10, 0);
  Tasks_Add((Task)loop3, 1, 0);

  // Start task scheduler
  Tasks_Start();
}

void loop1() {  // Serial
  gb.loop();
}

void loop2() {  // Send sensors / encoders data
  StaticJsonDocument<128> gen_feedback;
  gen_feedback[0] = 123;
  gen_feedback[1] = 456;

  gb.write("rg.f", gen_feedback);

  StaticJsonDocument<128> shooter_feedback;
  shooter_feedback[0] = group1_rm[0].unbound_tick;
  shooter_feedback[1] = group1_rm[0].speed;
  shooter_feedback[2] = group1_rm[0].output;
  shooter_feedback[3] = group1_rm[1].unbound_tick;
  shooter_feedback[4] = group1_rm[1].speed;
  shooter_feedback[5] = group1_rm[1].output;

  gb.write("rs.f", shooter_feedback);
}

void loop3() {  // PID Calculation
  tx_msg.id = 0x200;
  tx_msg.length = 8;

  for (int i = 0; i < GROUP1_MOTOR_COUNT; i++) {
    short output = group1_rm[i].get_output();
    tx_msg.data.byte[i * 2] = output >> 8;
    tx_msg.data.byte[i * 2 + 1] = output;
  }

  Can0.sendFrame(tx_msg);
}

// the loop function runs over and over again forever, runs ~14000 times per second
void loop() {
  Can0.watchFor();
  Can0.read(rx_msg);

  for (int i = 0; i < GROUP1_MOTOR_COUNT; i++) {
    if (group1_rm[i].handle_packet(rx_msg.id, rx_msg.data.byte)) break;
  }
}

```

### Worker Code

```py
from jen import *


def run(worker: WorkerController):
    worker.init()
    worker.use_clock(frequency=100)
    sm = worker.use_serial_manager()
    sm.whitelist.append(PortInfo(serial_number="5513132373735171A0B1", baudrate=115200))
    sm.whitelist.append(PortInfo(serial_number="7513131383235170F071", baudrate=115200))

    gb.start_gateway(UDPBroadcast("255.255.255.255", 7986))

    gen_output = gb.clone("rg.o")
    shooter_output = gb.clone("rs.o")

    while True:
        if isBtnJustPressed(RIGHT_L):
            gen_output[0] = not gen_output[0]

        gen_output[1] = isBtnPressing(RIGHT_U)
        gen_output[2] = isBtnPressing(RIGHT_R)

        if isBtnJustPressed(RIGHT_D):
            gen_output[3] = not gen_output[3]

        gb.write("rg.o", list(gen_output))

        shooter_output[0] = int(getAxis(LEFT_X) * 8192 * 19 * (45 / 360) * 7)
        shooter_output[1] = int(-getAxis(LEFT_Y) * 8192 * 19 * (150 / 360))

        gb.write("rs.o", list(shooter_output))

        ## print("local", gen_output)
        ## ## print("e", time.perf_counter())
        ## print("feedback", gb.read("rs.f"))

        worker.spin()
```


## ESP32 / Arduino Due Mini Car Example (Tested with Jerry's Mini Car):

### CPP Code

```cpp
#define INO_FILE

#include "jen.hpp"

#ifdef ESP32

#define PWMB 27
#define DIRB 14
#define DIRA 12
#define PWMA 13

#else 

#define PWMB 6
#define DIRB 7
#define DIRA 8
#define PWMA 9

#endif

void drive_update_callback(JsonVariant var) {
  JsonArray value = var.as<JsonArray>();

  float left = value[0].as<float>();
  float right = value[1].as<float>();

  digitalWrite(DIRA, right > 0 ? 1 : 0);
  digitalWrite(DIRB, left > 0 ? 0 : 1);

  analogWrite(PWMA, abs(right) * 255);
  analogWrite(PWMB, abs(left) * 255);

  static int count = 0;
  console << count++ << "\n";
}

void setup() {
  pinMode(PWMB, OUTPUT);
  pinMode(DIRB, OUTPUT);
  pinMode(DIRA, OUTPUT);
  pinMode(PWMA, OUTPUT);

  gb.watch("drive", drive_update_callback);

  gb.setup(115200);
}

void loop() {
  gb.loop();
  delay(0);
}

```

### Worker Code

```py
from jen import *


def clamp(n, minn, maxn):
    return max(min(maxn, n), minn)

def run(worker: WorkerController):
    worker.init()
    worker.use_clock(frequency=100)
    sm = worker.use_serial_manager()
    sm.whitelist.append(PortInfo(serial_number="557363239383510130D0", baudrate=115200))
    sm.whitelist.append(PortInfo(serial_number="6&21E92061&1&4", baudrate=115200))
    sm.whitelist.append(PortInfo(serial_number="", baudrate=115200))

    gb.start_gateway(UDPBroadcast("255.255.255.255", 7986))

    drive_output = [0, 0]

    while True:
        drive_output[0] = clamp(-isBtnPressing("kb:a") + isBtnPressing("kb:d") + isBtnPressing("kb:w") - isBtnPressing("kb:s"), -1, +1)
        drive_output[1] = clamp(-isBtnPressing("kb:d") + isBtnPressing("kb:a") + isBtnPressing("kb:w") - isBtnPressing("kb:s"), -1, +1)

        gb.write("drive", list(drive_output))

        worker.spin()

```
