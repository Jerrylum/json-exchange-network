#pragma once

#define PACKETIZER_USE_INDEX_AS_DEFAULT
#define PACKETIZER_USE_CRC_AS_DEFAULT

#define STL arx
#define STL_UINT8_VECTOR STL::vector<uint8_t, 128U>
#define STL_STRING_VECTOR STL::vector<String, 128>
#define STL_STOI(x) x.toInt()
#define JSON_DOC_SIZE 1024

#define DECLARE_WATCHER(type, name, path, body) \
  void name(JsonVariant t) {                    \
    type value = t.as<type>();                  \
    body                                        \
  }                                             \
  const char* name##_path = path;

#define START_WATCHER(name) gb.watch(name##_path, name);

#define DECLARE_GLOBAL_VARIABLE(type, name, def) \
  inline type& name() {                          \
    static type _##name def;                     \
    return _##name;                              \
  }

#define DECLARE_GLOBAL_ARRAY(type, name, size) \
  inline type* name() {                        \
    static type _##name[size];                 \
    return _##name;                            \
  }

#include <ArduinoJson.h>
#include <ArxContainer.h>
#include <Packetizer.h>

#include "event_emitter.hpp"


///////////////////////////////////////////////////////////////////////////////
///////////////////CONSOLE/////////////////////////////////////////////////////
///////////////////////////////////////////////////////////////////////////////

namespace jen {

class Console {};

};  // namespace jen

static jen::Console console;

template <class T>
inline jen::Console& operator<<(jen::Console& stream, T arg) {
  String message = String(arg);
  byte plain[message.length() + 1];
  message.getBytes(plain, message.length() + 1);

  Packetizer::send(Serial, 4, plain, message.length() + 1);
  return stream;
};

///////////////////////////////////////////////////////////////////////////////
///////////////////MAIN BODY///////////////////////////////////////////////////
///////////////////////////////////////////////////////////////////////////////

namespace jen {

DECLARE_GLOBAL_ARRAY(uint8_t, serial_rx, JSON_DOC_SIZE);
DECLARE_GLOBAL_VARIABLE(int, serial_rx_index, = 0);
DECLARE_GLOBAL_VARIABLE(EventEmitter<JsonVariant>, emitter, );
DECLARE_GLOBAL_VARIABLE(String, conn_id, = "");

// static const arduino::packetizer::Packet& dd() {
//   return Packetizer::decode(serial_rx(), serial_rx_index());
// }
inline String readNTBS(STL_UINT8_VECTOR data, int& idx) {
  String result = "";
  while (data[idx++] != 0) {
    result += (char)data[idx - 1];
  }
  return result;
}

const arduino::packetizer::Packet& _decode();

class Globals {
 public:
  inline void loop() {
    while (Serial.available() > 0) {
      if (serial_rx_index() < 2048 && (serial_rx()[serial_rx_index()++] = Serial.read()) == 0) {
        const auto& p_out = _decode();
        serial_rx_index() = 0;

        const auto data = p_out.data;

        int idx = 0;

        if (p_out.index == 2) {
          jen::conn_id() = readNTBS(data, idx);

          StaticJsonDocument<JSON_DOC_SIZE> data;
          data["available"] = true;
          data["type"] = "tty";
          data.createNestedArray("watch");
          write("device", data);

          sync();

          console << "Registered id " << conn_id() << "\n";
        } else if (p_out.index == 3) {
          StaticJsonDocument<JSON_DOC_SIZE> cache;

          String path = readNTBS(data, idx);
          DeserializationError error = deserializeMsgPack(cache, &data[idx]);
          if (error) {
            console << "deserializeMsgPack() failed: " << error.f_str() << "\n";
            return;
          }

          emitter().emit(path.c_str(), cache.as<JsonVariant>());
        }
      }
    }
  }

  inline void setup() {
    Serial.begin(115200);
    Serial.setTimeout(1);
  }

  template <typename TValue>
  bool write(String path, const TValue val) {
    // not ready yet
    if (jen::conn_id() == "") return false;

    // Changing all channels is not allowed
    if (path.length() == 0) return false;

    // Changing the root key is not allowed
    if (path.indexOf('.', 0) == -1) return false;

    StaticJsonDocument<JSON_DOC_SIZE> data;
    data.set(val);

    int path_size = path.length() + 1;
    int data_size = measureMsgPack(data);

    byte send[path_size + data_size];

    path.getBytes(send, path_size);
    serializeMsgPack(data, &send[path_size], data_size);

    Packetizer::send(Serial, 3, send, path_size + data_size);
  }

  inline void sync() {
    StaticJsonDocument<128> send;
    for (unsigned int i = 0; i < EVENT_EMITTER_MAX_LISTENERS; ++i) {
      if (emitter().listeners[i] != NULL) {
        send.add(emitter().listeners[i]->getEventName());
      }
    }
    write("conn." + conn_id() + ".watch", send);
  }

  inline void watch(String path, void (*cb)(JsonVariant t)) {
    emitter().addListener(path.c_str(), cb);
    if (conn_id() != "") sync();
  }
};

}  // namespace jen

static jen::Globals gb;
