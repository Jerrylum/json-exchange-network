#pragma once

class PIDImpl {
 public:
  PIDImpl(double dt, double _max_val, double _min_val, double Kp, double Kd, double Ki)
      : _dt(dt), _max_val(_max_val), _min_val(_min_val), _Kp(Kp), _Kd(Kd), _Ki(Ki), _pre_error(0), _integral(0){};

  ~PIDImpl(){};

  inline double calculate(double setpoint, double pv) {
    // Calculate error
    double error = setpoint - pv;

    // Proportional term
    double Pout = _Kp * error;

    // Integral term
    _integral += error * _dt;
    double Iout = _Ki * _integral;

    // Derivative term
    double derivative = (error - _pre_error) / _dt;
    double Dout = _Kd * derivative;

    // Calculate total output
    double output = Pout + Iout + Dout;

    // Restrict to max/min
    if (output > _max_val)
      output = _max_val;
    else if (output < _min_val)
      output = _min_val;

    // Save error to previous error
    _pre_error = error;

    return output;
  }

  double _dt;
  double _max_val;
  double _min_val;
  double _Kp;
  double _Kd;
  double _Ki;
  double _pre_error;
  double _integral;
};

class PID {
 public:
  PIDImpl *_pimpl;

  // Kp -  proportional gain
  // Ki -  Integral gain
  // Kd -  derivative gain
  // dt -  loop interval time
  // max - maximum value of manipulated variable
  // min - minimum value of manipulated variable
  PID(double dt, double _max_val, double _min_val, double Kp, double Kd, double Ki) {
    _pimpl = new PIDImpl(dt, _max_val, _min_val, Kp, Kd, Ki);
  }

  // Returns the manipulated variable given a setpoint and current process value
  inline double calculate(double setpoint, double pv) { return _pimpl->calculate(setpoint, pv); }

  ~PID() { delete _pimpl; }
};
