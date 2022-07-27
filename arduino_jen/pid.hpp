#pragma once

// PID
class PIDImpl;
class PID {
    public:
        // Kp -  proportional gain
        // Ki -  Integral gain
        // Kd -  derivative gain
        // dt -  loop interval time
        // max - maximum value of manipulated variable
        // min - minimum value of manipulated variable
        PID(double dt, double _max, double _min, double Kp, double Kd, double Ki);

        // Returns the manipulated variable given a setpoint and current process value
        double calculate(double setpoint, double pv);
        ~PID();

    private:
        PIDImpl *pimpl;
};

class PIDImpl {
    public:
        PIDImpl(double dt, double _max, double _min, double Kp, double Kd, double Ki);
        ~PIDImpl();
        double calculate(double setpoint, double pv);

        double _dt;
        double _max;
        double _min;
        double _Kp;
        double _Kd;
        double _Ki;
        double _pre_error;
        double _integral;
};
