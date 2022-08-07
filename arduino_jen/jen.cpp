#include "jen.hpp"

namespace jen {

uint8_t serial_rx[JSON_DOC_SIZE];
int serial_rx_index;

EventEmitter<JsonVariant> emitter;

String conn_id = "";

// this can not be an inline method because of "internal compiler error: in strip_typedefs, at cp/tree.c:1295"
void Globals::loop() {
  while (Serial.available() > 0) {
    if (serial_rx_index < 2048 && (serial_rx[serial_rx_index++] = Serial.read()) == 0) {
      const auto& p_out = Packetizer::decode(serial_rx, serial_rx_index);
      serial_rx_index = 0;

      const auto data = p_out.data;

      int idx = 0;

      if (p_out.index == 2) {
        jen::conn_id = readNTBS(data, idx);

        StaticJsonDocument<JSON_DOC_SIZE> data;
        data["available"] = true;
        data["type"] = "tty";
        data.createNestedArray("watch");
        write("device", data);

        sync();

        consolePrint("Registered id " + conn_id);
      } else if (p_out.index == 3) {
        StaticJsonDocument<JSON_DOC_SIZE> cache;
        
        String path = readNTBS(data, idx);
        DeserializationError error = deserializeMsgPack(cache, &data[idx]);
        if (error) {
          console << "deserializeMsgPack() failed: " << error.f_str();
          return;
        }

        emitter.emit(path.c_str(), cache.as<JsonVariant>());
      }
    }
  }
}

}  // namespace jen

void consolePrint(String msg) { console << msg; }