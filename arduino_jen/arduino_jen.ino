#include <Tasks.h>
#include <due_can.h>

#include "jen.hpp"

#define Motor_Num 2
#define EN 6
#define AIR_PA 3
#define AIR_PB 2
#define AIR_EA 4
#define AIR_EB 5
#define AIR_PLATFORM_UP 7
#define AIR_PLATFORM_DOWN 8

CAN_FRAME tx_msg, rx_msg;

int rm_output[Motor_Num] = {0};

void sendRMMotorCurrent() {
  for (int i = 0; i < 2; i++) {
    tx_msg.data.byte[i * 2] = rm_output[i] >> 8;
    tx_msg.data.byte[i * 2 + 1] = rm_output[i];
  }

  Can0.sendFrame(tx_msg);
}

DECLARE_WATCHER(String, test_watcher, "robot.run", console << "Updated " << value;)

static int yy = 0;

DECLARE_WATCHER(JsonObject, platform, "robot_gerenal.output",
  bool BLDC = value["BLDC"].as<bool>();
  bool elevator = value["elevator"].as<bool>();
  bool pusher = value["pusher"].as<bool>();
  bool platform = value["platform"].as<bool>();

  digitalWrite(EN, BLDC ? HIGH : LOW);
  digitalWrite(AIR_EA, elevator ? LOW : HIGH);
  digitalWrite(AIR_EB, elevator ? HIGH : LOW);
  digitalWrite(AIR_PA, pusher ? LOW : HIGH);
  digitalWrite(AIR_PB, pusher ? HIGH : LOW);
  digitalWrite(AIR_PLATFORM_UP, platform ? LOW : HIGH);
  digitalWrite(AIR_PLATFORM_DOWN, platform ? HIGH : LOW);

)


void setup() {
  // initialize digital pin LED_BUILTIN as an output.
  pinMode(LED_BUILTIN, OUTPUT);

  pinMode(EN, OUTPUT);
  pinMode(AIR_PA, OUTPUT);
  pinMode(AIR_EA, OUTPUT);
  pinMode(AIR_PB, OUTPUT);
  pinMode(AIR_EB, OUTPUT);
  pinMode(AIR_PLATFORM_UP, OUTPUT);
  pinMode(AIR_PLATFORM_DOWN, OUTPUT);

  START_WATCHER(test_watcher);

  START_WATCHER(platform);

  Can0.begin(CAN_BPS_1000K);  //  For communication with RM motors

  tx_msg.id = 0x200;
  tx_msg.length = 8;
  
  gb.setup();

  Tasks_Add((Task)loop1, 1, 0);
  Tasks_Add((Task)loop2, 1000, 0);
  Tasks_Add((Task)loop3, 1, 0);

  // Start task scheduler
  Tasks_Start();
}

void loop1() {  // Serial
  gb.loop();
}

static int count_time = 0;

void loop2() {  // Send sensors / encoders data
  StaticJsonDocument<128> test;
  test["t"] = count_time;

  gb.write("robot.time", count_time);
  gb.write("robot.test", test);

  // count_time = 0;
}

void loop3() {  // PID Calculation
  int result;

  // result = shooterx_pos_pid.calculate(shooterx_target_pos, rm_unbound_position[0]);
  // rm_output[0] = result;
  // shooterx_debug_speed_log = result;

  // result = shootery_pos_pid.calculate(shootery_target_pos, rm_unbound_position[1]);
  // rm_output[1] = shootery_debug_speed_log = result;

  sendRMMotorCurrent();
}

// the loop function runs over and over again forever, runs ~14000 times per second
void loop() {
  static int local_count = 0;

  if (local_count++ > 10) {
    local_count = 0;
    count_time += 10;
    delay(1);
  }

  Can0.watchFor();
  Can0.read(rx_msg);

  // digitalWrite(LED_BUILTIN, HIGH);  // turn the LED on (HIGH is the voltage level)
  // delay(500);                       // wait for a second
  // digitalWrite(LED_BUILTIN, LOW);   // turn the LED off by making the voltage LOW
  // delay(500);                       // wait for a second
}
