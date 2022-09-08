#include <CAN.h>
#include <ESP32Servo.h>

#define INO_FILE

#include "jen.hpp"

#include "pid.hpp"
#include "bounding_helper.hpp"
#include "rm_motor.hpp"


#define ELEVATOR 18
#define CLAW_X 23
#define CLAW_Y 25
#define INTAKE 27

Servo elevator;
Servo claw_x;
Servo claw_y;

int elevator_pos;
int claw_x_pos;
int claw_y_pos;

#define GROUP1_MOTOR_COUNT 4
RMM3508Motor group1_rm[GROUP1_MOTOR_COUNT] = {
  RMM3508Motor(0, DIRECT_OUTPUT_MODE),
  RMM3508Motor(1, DIRECT_OUTPUT_MODE),
  RMM3508Motor(2, DIRECT_OUTPUT_MODE),
  RMM3508Motor(3, POS_PID_MODE)
};

unsigned char can_tx[8] = {0};

// Task function, Task name, Stack size (bytes), Task parameter, Priority, Task handle, Core ID
#define CREATE_ESP32_TASK(name) \
  static TaskHandle_t name##_handle; \
  xTaskCreatePinnedToCore(name, #name, 10000, NULL, 1, &name##_handle, 0);


void setting_update_callback(JsonVariant var) {
  JsonObject value = var.as<JsonObject>();

  JsonVariant c_pos_pid_from = value["catapult"]["pos_pid"];
  JsonVariant c_speed_pid_from = value["catapult"]["speed_pid"];

  PIDImpl* c_pos_pid_to = group1_rm[3].pos_pid;
  c_pos_pid_to->_max_val = c_pos_pid_from["max"] | 0.0;
  c_pos_pid_to->_min_val = c_pos_pid_from["min"] | 0.0;
  c_pos_pid_to->_Kp = c_pos_pid_from["p"] | 0.0;
  c_pos_pid_to->_Kd = c_pos_pid_from["d"] | 0.0;
  c_pos_pid_to->_Ki = c_pos_pid_from["i"] | 0.0;

  PIDImpl* c_speed_pid_to = group1_rm[3].speed_pid;
  c_speed_pid_to->_max_val = c_speed_pid_from["max"] | 0.0;
  c_speed_pid_to->_min_val = c_speed_pid_from["min"] | 0.0;
  c_speed_pid_to->_Kp = c_speed_pid_from["p"] | 0.0;
  c_speed_pid_to->_Kd = c_speed_pid_from["d"] | 0.0;
  c_speed_pid_to->_Ki = c_speed_pid_from["i"] | 0.0;
}


void drive_update_callback(JsonVariant var) {
  JsonArray value = var.as<JsonArray>();

  bool intake = value[0].as<bool>();
  digitalWrite(INTAKE, intake ? HIGH : LOW);

  elevator.write(value[1].as<int>());
  claw_x.write(value[2].as<int>());
  claw_y.write(value[3].as<int>());

  static int count = 0;
  console << count++ << "\n";
}

void catapult_trigger_callback(JsonVariant var) {
  int flag = var.as<int>();
  
  if (flag == 1 || flag == -1) {
    if (group1_rm[3].output_mode != POS_PID_MODE) {
      group1_rm[3].target_tick = group1_rm[3].unbound_tick;
    } else {
      group1_rm[3].target_tick -= 8192 * 19;
    }
    group1_rm[3].output_mode = POS_PID_MODE;
  } else if (flag == 2) {
    group1_rm[3].target_speed = -1000;
    group1_rm[3].output_mode = SPEED_PID_MODE;
  } else {
    group1_rm[3].output = 0;
    group1_rm[3].output_mode = DIRECT_OUTPUT_MODE;
  }
}

void can_callback(int packetSize) {
  if (packetSize) {
    int rx_id = CAN.packetId();
    unsigned char can_rx[8];

    for (int j = 0; j < 8; j++){
      can_rx[j] = CAN.read();
    }

    for (int i = 0; i < GROUP1_MOTOR_COUNT; i++) {
      if (group1_rm[i].handle_packet(rx_id, can_rx)) break;
    }
  }
}

void setup() {
  pinMode(INTAKE, OUTPUT);
  elevator.setPeriodHertz(50);
  elevator.attach(ELEVATOR, 500, 2500);
  elevator.write(170);
  claw_x.setPeriodHertz(50);
  claw_x.attach(CLAW_X, 500, 2500);
  claw_x.write(40);
  claw_y.setPeriodHertz(50);
  claw_y.attach(CLAW_Y, 500, 2500);
  claw_y.write(100);

  gb.watch("setting", setting_update_callback);
  gb.watch("drive", drive_update_callback);
  gb.watch("catapult_trigger", catapult_trigger_callback);

  gb.setup(921600);

  CAN.onReceive(can_callback);
  if (!CAN.begin(1000E3)) {
    console << "CAN init failed\n";
  }

  CREATE_ESP32_TASK(sensor_feedback_task);
  CREATE_ESP32_TASK(gb_loop_task);
}

void sensor_feedback_task(void * pvParameters) {
  while (true) {
    StaticJsonDocument<256> feedback;

    // for (int i = 0; i < GROUP1_MOTOR_COUNT; i++) {
    //   feedback[i * 3 + 0] = group1_rm[i].unbound_tick;
    //   feedback[i * 3 + 1] = group1_rm[i].speed;
    //   feedback[i * 3 + 2] = group1_rm[i].output;
    // }

    feedback[0] = group1_rm[3].unbound_tick;
    feedback[1] = group1_rm[3].speed;
    feedback[2] = group1_rm[3].output;

    // for (int i = 0; i < GROUP1_MOTOR_COUNT; i++) {
    //   feedback[i] = group1_rm[i].unbound_tick;
    // }

    gb.write("feedback", feedback);
    
    delay(20);
  }
}

void gb_loop_task(void * pvParameters) {
  while (true) {
    gb.loop();
    delay(1);
  }
}

void loop() {
  CAN.beginPacket(0x200);

  for (int i = 0; i < GROUP1_MOTOR_COUNT; i++) {
    short output = group1_rm[i].get_output();
    can_tx[i * 2] = output >> 8;
    can_tx[i * 2 + 1] = output;
  }

  CAN.write(can_tx, 8);
  CAN.endPacket();

  delay(5);
}
