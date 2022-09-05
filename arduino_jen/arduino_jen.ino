#include <CAN.h>

#define INO_FILE

#include "jen.hpp"

#include "pid.hpp"
#include "bounding_helper.hpp"
#include "rm_motor.hpp"

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

#define GROUP1_MOTOR_COUNT 2
RMM3508Motor group1_rm[GROUP1_MOTOR_COUNT] = {RMM3508Motor(0, POS_PID_MODE), RMM3508Motor(1, POS_PID_MODE)};

// Task function, Task name, Stack size (bytes), Task parameter, Priority, Task handle, Core ID
#define CREATE_ESP32_TASK(name) \
  static TaskHandle_t name##_handle; \
  xTaskCreatePinnedToCore(name, #name, 10000, NULL, 1, &name##_handle, 0);


void drive_update_callback(JsonVariant var) {
  JsonArray value = var.as<JsonArray>();

  // value[0].as<float>();
  // TODO

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
  pinMode(PWMB, OUTPUT);
  pinMode(DIRB, OUTPUT);
  pinMode(DIRA, OUTPUT);
  pinMode(PWMA, OUTPUT);

  gb.watch("drive", drive_update_callback);

  gb.setup(115200);

  CAN.onReceive(can_callback);
  if (!CAN.begin(1000E3)) {
    console << "CAN init failed\n";
  }

  CREATE_ESP32_TASK(sensor_feedback_task);
  CREATE_ESP32_TASK(motor_update_task);
}

void sensor_feedback_task(void * pvParameters) {
  while (true) {
    // StaticJsonDocument<128> gen_feedback;
    // gen_feedback[0] = 123;
    // gen_feedback[1] = 456;
    // gb.write("rg.f", gen_feedback);
    
    console << "send data...\n";
    delay(1000);
  }
}

void motor_update_task(void * pvParameters) {
  while (true) {
    CAN.beginPacket(0x200);
    unsigned char can_tx[8];

    for (int i = 0; i < GROUP1_MOTOR_COUNT; i++) {
      short output = group1_rm[i].get_output();
      can_tx[i * 2] = output >> 8;
      can_tx[i * 2 + 1] = output;
    }

    CAN.write(can_tx, 8);
    CAN.endPacket();

    delay(10);
  }
}

void loop() {
  gb.loop();
  delay(0);
}
