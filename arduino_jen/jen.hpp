#pragma once

#define PACKETIZER_USE_INDEX_AS_DEFAULT
#define PACKETIZER_USE_CRC_AS_DEFAULT

#define STL arx
#define STL_UINT8_VECTOR STL::vector<uint8_t, 128U>
#define STL_STRING_VECTOR STL::vector<String, 128>
#define STL_STOI(x) x.toInt()
#define JSON_DOC_SIZE 1024

#define DECLARE_WATCHER(type, name, path, body) \
  void name (JsonVariant t) { \
    type value = t.as<type>(); \
    body \
  } \
  const char* name##_path = path;

#define START_WATCHER(name) \
  gb.watch(name##_path, name);


#include <ArduinoJson.h>
#include <ArxContainer.h>
#include <Packetizer.h>


void consolePrint(String msg);

#include "EventEmitter.hpp"

namespace jen {

extern EventEmitter<JsonVariant> emitter;

extern String deviceName;

inline String readNTBS(STL_UINT8_VECTOR data, int& idx) {
  String result = "";
  while (data[idx++] != 0) {
    result += (char)data[idx - 1];
  }
  return result;
}

class Console {};

class Globals {
 public:

  void loop();

  inline void setup() {
    Serial.begin(115200);
    Serial.setTimeout(1);
  }

  template <typename TValue>
  bool write(String path, const TValue val) {
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

    Packetizer::send(Serial, 2, send, path_size + data_size);
  }

  inline void sync() {
    StaticJsonDocument<128> send;
    for (unsigned int i = 0; i < EVENT_EMITTER_MAX_LISTENERS; ++i) {
      if (emitter.listeners[i] != NULL) {
        send.add(emitter.listeners[i]->getEventName());
      }
    }
    write("device." + deviceName + ".watch", send);
  }
  
  inline void watch(String path, void (*cb)(JsonVariant t)) {
    emitter.addListener(path.c_str(), cb);
    if (deviceName != "") sync();
  }
};

}  // namespace jen

static jen::Globals gb;

static jen::Console console;

template <class T>
inline jen::Console& operator<<(jen::Console& stream, T arg) {
  String message = String(arg);
  byte plain[message.length() + 1];
  message.getBytes(plain, message.length() + 1);

  Packetizer::send(Serial, 4, plain, message.length() + 1);
  return stream;
};
