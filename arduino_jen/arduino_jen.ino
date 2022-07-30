#include <Tasks.h>
#include <due_can.h>

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

void sendRMMotorCurrent() {
  tx_msg.id = 0x200;
  tx_msg.length = 8;

  for (int i = 0; i < GROUP1_MOTOR_COUNT; i++) {
    short output = group1_rm[i].get_output();
    tx_msg.data.byte[i * 2] = output >> 8;
    tx_msg.data.byte[i * 2 + 1] = output;
  }

  Can0.sendFrame(tx_msg);
}

DECLARE_WATCHER(JsonObject, shooter_setting, "rs.s",
  JsonVariant sx = value["sx"]["pid"];
  JsonVariant sy = value["sy"]["pid"];

  PIDImpl* sx_pid = group1_rm[0].pos_pid;
  sx_pid->_max = sx["max"] | 0.0;
  sx_pid->_min = sx["min"] | 0.0;
  sx_pid->_Kp = sx["p"] | 0.0;
  sx_pid->_Kd = sx["d"] | 0.0;
  sx_pid->_Ki = sx["i"] | 0.0;

  PIDImpl* sy_pid = group1_rm[1].pos_pid;
  sy_pid->_max = sy["max"] | 0.0;
  sy_pid->_min = sy["min"] | 0.0;
  sy_pid->_Kp = sy["p"] | 0.0;
  sy_pid->_Kd = sy["d"] | 0.0;
  sy_pid->_Ki = sy["i"] | 0.0;

  static int count = 0;
  console << "updated pid" << count++;
)

DECLARE_WATCHER(JsonObject, gen_output, "rg.o",
  bool BLDC = value["BLDC"].as<bool>();
  bool elevator = value["e"].as<bool>();
  bool pusher = value["pu"].as<bool>();
  bool platform = value["pl"].as<bool>();

  digitalWrite(EN, BLDC ? HIGH : LOW);
  digitalWrite(AIR_EA, elevator ? LOW : HIGH);
  digitalWrite(AIR_EB, elevator ? HIGH : LOW);
  digitalWrite(AIR_PA, pusher ? LOW : HIGH);
  digitalWrite(AIR_PB, pusher ? HIGH : LOW);
  digitalWrite(AIR_PLATFORM_UP, platform ? LOW : HIGH);
  digitalWrite(AIR_PLATFORM_DOWN, platform ? HIGH : LOW);

  static int count = 0;
  console << "updated " << count++;
)

DECLARE_WATCHER(JsonObject, shooter_output, "rs.o",
  int x = value["sx"]["pos"].as<int>();
  int y = value["sy"]["pos"].as<int>();

  group1_rm[0].target_tick = x;
  group1_rm[1].target_tick = y;

  // static int count = 0;
  // console << "shooter updated " << count++;
  // console << x;
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

  gb.setup();

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
  gen_feedback["s1"] = 123;
  gen_feedback["s2"] = 456;

  gb.write("rg.f", gen_feedback);

  StaticJsonDocument<128> shooter_feedback;
  shooter_feedback["sx"]["pos"] = group1_rm[0].unbound_tick;
  shooter_feedback["sx"]["sp"] = group1_rm[0].speed;
  shooter_feedback["sx"]["out"] = group1_rm[0].output;
  shooter_feedback["sy"]["pos"] = group1_rm[1].unbound_tick;
  shooter_feedback["sy"]["sp"] = group1_rm[1].speed;
  shooter_feedback["sy"]["out"] = group1_rm[1].output;

  gb.write("rs.f", shooter_feedback);
}

void loop3() {  // PID Calculation
  int result;

  sendRMMotorCurrent();
}

// the loop function runs over and over again forever, runs ~14000 times per second
void loop() {
  Can0.watchFor();
  Can0.read(rx_msg);

  for (int i = 0; i < GROUP1_MOTOR_COUNT; i++) {
    if (group1_rm[i].handle_packet(rx_msg.id, rx_msg.data.byte)) break;
  }
}
