#include "pid.hpp"

PID::PID(double dt, double _max, double _min, double Kp, double Kd, double Ki) {
    pimpl = new PIDImpl(dt, _max, _min, Kp, Kd, Ki);
}

double PID::calculate(double setpoint, double pv) {
    return pimpl->calculate(setpoint,pv);
}

PID::~PID() {
    delete pimpl;
}

PIDImpl::PIDImpl(double dt, double _max, double _min, double Kp, double Kd, double Ki) :
    _dt(dt),
    _max(_max),
    _min(_min),
    _Kp(Kp),
    _Kd(Kd),
    _Ki(Ki),
    _pre_error(0),
    _integral(0) { }

double PIDImpl::calculate(double setpoint, double pv) {
    
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
    if( output > _max )
        output = _max;
    else if( output < _min )
        output = _min;

    // Save error to previous error
    _pre_error = error;

    return output;
}

PIDImpl::~PIDImpl() { }
