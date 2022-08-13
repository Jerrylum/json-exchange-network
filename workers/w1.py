from jen import *


def run(worker: WorkerController):
    worker.init()
    worker.use_clock(frequency=100)
    sm = worker.use_serial_manager()
    sm.whitelist.append(PortInfo(serial_number="5513132373735171A0B1", baudrate=115200))
    sm.whitelist.append(PortInfo(serial_number="7513131383235170F071", baudrate=115200))

    gb.connect_server(("127.0.0.1", 7984))

    gen_output = gb.clone("rg.o")
    shooter_output = gb.clone("rs.o")

    while True:
        if isBtnJustPressed(RIGHT_L):
            gen_output[0] = not gen_output[0]

        gen_output[1] = isBtnPressing(RIGHT_U)
        gen_output[2] = isBtnPressing(RIGHT_R)

        if isBtnJustPressed(RIGHT_D):
            gen_output[3] = not gen_output[3]

        gb.write("rg.o", list(gen_output))

        shooter_output[0] = int(getAxis(LEFT_X) * 8192 * 19 * (45 / 360) * 7)
        shooter_output[1] = int(-getAxis(LEFT_Y) * 8192 * 19 * (150 / 360))

        gb.write("rs.o", list(shooter_output))

        # print("local", gen_output)
        # # print("e", time.perf_counter())
        # print("feedback", gb.read("rs.f"))

        worker.spin()
