#include <Tasks.h>
#include <due_can.h>

#include "jen.hpp"

#include "pid.hpp"
#include "bounding_helper.hpp"


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
int rm_speed[Motor_Num];
int rm_gearbox_position[Motor_Num];
int rm_unbound_position[Motor_Num];
bounding_helper rm_bounding_helper[Motor_Num];

//PID shooterx_pos_pid = PID(1, 2000, -2000, 0.30, 7000, 0);
PID shooterx_pos_pid = PID(1, 2000, -2000, 0.35, 180, 0);
int shooterx_target_pos = 0;

PID shootery_pos_pid = PID(1, 4000, -4000, 0.35, 180, 0);
int shootery_target_pos = 0; // 0.02 -> 0.022 -> 0.025

int shooterx_debug_speed_log = 0;
int shootery_debug_speed_log = 0;

void sendRMMotorCurrent() {
  for (int i = 0; i < 2; i++) {
    tx_msg.data.byte[i * 2] = rm_output[i] >> 8;
    tx_msg.data.byte[i * 2 + 1] = rm_output[i];
  }

  Can0.sendFrame(tx_msg);
}

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
  float x = value["sx"]["pos"].as<float>();
  float y = value["sy"]["pos"].as<float>();

  shooterx_target_pos = x;
  shootery_target_pos = y;

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

  START_WATCHER(gen_output);
  START_WATCHER(shooter_output);

  Can0.begin(CAN_BPS_1000K);  //  For communication with RM motors

  tx_msg.id = 0x200;
  tx_msg.length = 8;

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
  // StaticJsonDocument<128> gen_feedback;
  // gen_feedback["sensor1_value"] = 123;
  // gen_feedback["sensor2_value"] = 456;

  // gb.write("robot_gerenal.feedback", gen_feedback);

  StaticJsonDocument<128> shooter_feedback;
  shooter_feedback["sx"]["now_pos"] = rm_unbound_position[0];
  shooter_feedback["sx"]["now_speed"] = rm_speed[0];
  shooter_feedback["sx"]["output_speed"] = shooterx_debug_speed_log;
  shooter_feedback["sy"]["now_pos"] = rm_unbound_position[1];
  shooter_feedback["sy"]["now_speed"] = rm_speed[1];
  shooter_feedback["sy"]["output_speed"] = shootery_debug_speed_log;

  gb.write("rs.f", shooter_feedback);
}

void loop3() {  // PID Calculation
  int result;

  result = shooterx_pos_pid.calculate(shooterx_target_pos, rm_unbound_position[0]);
  rm_output[0] = result;
  shooterx_debug_speed_log = result;

  result = shootery_pos_pid.calculate(shootery_target_pos, rm_unbound_position[1]);
  rm_output[1] = shootery_debug_speed_log = result;

  sendRMMotorCurrent();
}

// the loop function runs over and over again forever, runs ~14000 times per second
void loop() {
  Can0.watchFor();
  Can0.read(rx_msg);

  int motor_idx = rx_msg.id - 0x201;
  int gearbox_pos = rx_msg.data.byte[0] << 8 | rx_msg.data.byte[1];
  rm_unbound_position[motor_idx] = rm_bounding_helper[motor_idx](gearbox_pos);

  //feedback
  rm_speed[rx_msg.id - 0x201] = rx_msg.data.byte[2] << 8 | rx_msg.data.byte[3];
}
