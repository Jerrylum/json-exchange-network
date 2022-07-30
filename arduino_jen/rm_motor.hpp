#include "bounding_helper.hpp"
#include "pid.hpp"

#define DIRECT_OUTPUT_MODE (-1)
#define POS_PID_MODE (0)
#define SPEED_PID_MODE (1)

class RMM3508Motor {
private:
  unsigned char _motor_id = 0; // 0 based

public:
  // setting
  PIDImpl *pos_pid;
  PIDImpl *speed_pid;
  class bounding_helper bounding_helper;

  // feedback
  long gearbox_tick = 0;
  long unbound_tick = 0;
  short speed = 0;

  // output
  short output_mode = DIRECT_OUTPUT_MODE;
  short output = 0;

  // target
  long target_tick = 0;
  long target_speed = 0;

  RMM3508Motor(unsigned char motor_id, short output_mode)
      : _motor_id(motor_id), output_mode(output_mode) {
    pos_pid = new PIDImpl(1, 0, 0, 0, 0, 0);
    speed_pid = new PIDImpl(1, 0, 0, 0, 0, 0);
  }

  inline bool handle_packet(unsigned int msg_id, unsigned char *data) {
    if (msg_id != _motor_id + 0x201)
      return false;

    gearbox_tick = data[0] << 8 | data[1];
    unbound_tick = bounding_helper(gearbox_tick);
    speed = data[2] << 8 | data[3];

    return true;
  }

  inline short get_output() {
    if (output_mode == POS_PID_MODE)
      output = pos_pid->calculate(target_tick, unbound_tick);
    else if (output_mode == SPEED_PID_MODE)
      output = speed_pid->calculate(target_speed, speed);
    
    return output;
  }
};