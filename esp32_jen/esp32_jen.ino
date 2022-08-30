#define INO_FILE

#include "jen.hpp"

#define PWMB 27
#define DIRB 14
#define DIRA 12
#define PWMA 13


DECLARE_WATCHER(JsonArray, gen_output, "drive",
  float left = value[0].as<float>();
  float right = value[1].as<float>();

  digitalWrite(DIRA, right > 0 ? 1 : 0);
  digitalWrite(DIRB, left > 0 ? 0 : 1);

  analogWrite(PWMA, abs(right) * 255);
  analogWrite(PWMB, abs(left) * 255);

  static int count = 0;
  console << count++ << "\n";
)

void setup() {
  pinMode(PWMB, OUTPUT);
  pinMode(DIRB, OUTPUT);
  pinMode(DIRA, OUTPUT);
  pinMode(PWMA, OUTPUT);

  delay(200);

  START_WATCHER(gen_output);

  gb.setup(115200);
}

void loop() {
  gb.loop();
  delay(0);
}
