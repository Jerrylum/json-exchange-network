#include "jen.hpp"

namespace jen {

// this can not be an inline method because of "internal compiler error: in strip_typedefs, at cp/tree.c:1295"
const arduino::packetizer::Packet& _decode() {
  return Packetizer::decode(serial_rx(), serial_rx_index());
}

}  // namespace jen
