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
  RMM3508Motor(0, POS_PID_MODE),
  RMM3508Motor(1, POS_PID_MODE),
  RMM3508Motor(2, POS_PID_MODE),
  RMM3508Motor(3, DIRECT_OUTPUT_MODE)
};

unsigned char can_tx[8] = {0};

// Task function, Task name, Stack size (bytes), Task parameter, Priority, Task handle, Core ID
#define CREATE_ESP32_TASK(name) \
  static TaskHandle_t name##_handle; \
  xTaskCreatePinnedToCore(name, #name, 10000, NULL, 1, &name##_handle, 0);


void drive_update_callback(JsonVariant var) {
  JsonArray value = var.as<JsonArray>();

  bool intake = value[0].as<bool>();
  digitalWrite(INTAKE, intake ? HIGH : LOW);

  elevator.write(value[1].as<int>());
  claw_x.write(value[2].as<int>());
  claw_y.write(value[3].as<int>());
  group1_rm[3].output = value[4].as<int>();

  static int count = 0;
  console << count++ << "\n";
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

  gb.watch("drive", drive_update_callback);

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

    for (int i = 0; i < GROUP1_MOTOR_COUNT; i++) {
      feedback[i] = group1_rm[i].unbound_tick;
    }

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
