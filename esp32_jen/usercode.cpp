#include "jen.hpp"


// XXX: Method declaration in user area instead of in jen.hpp
// This can not be an inline method or declared in *.ino file because of 
// "internal compiler error: in strip_typedefs, at cp/tree.c:1295" error
const arduino::packetizer::Packet& jen::decode_packet() {
  return Packetizer::decode(jen::serial_rx(), jen::serial_rx_index());
}

// user code here ...
