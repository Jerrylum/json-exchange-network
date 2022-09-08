from jen import *


def run(worker: WorkerController):
    worker.init()
    worker.use_clock(frequency=100)
    sm = worker.use_serial_manager()
    sm.whitelist.append(PortInfo(serial_number="5513132373735171A0B1", baudrate=115200))
    sm.whitelist.append(PortInfo(serial_number="7513131383235170F071", baudrate=115200))
    sm.whitelist.append(PortInfo(serial_number="0001", baudrate=921600))

    gb.start_gateway(UDPBroadcast("255.255.255.255", 7986))

    drive = gb.clone("drive")
    catapult_trigger = 0

    while True:

        drive[0] = isBtnPressing("kb:i")

        elevator_delta = (isBtnPressing("kb:o") - isBtnPressing("kb:l"))
        claw_x_delta = (isBtnPressing("kb:Right") - isBtnPressing("kb:Left"))
        claw_y_delta = (isBtnPressing("kb:Up") - isBtnPressing("kb:Down"))

        drive[1] = max(80, min(drive[1] + elevator_delta, 170))
        drive[2] = max(0, min(drive[2] + claw_x_delta, 140))
        drive[3] = max(0, min(drive[3] + claw_y_delta, 110))

        if isBtnJustPressed("kb:g"):
            catapult_trigger = 2
        if isBtnJustReleased("kb:g"):
            catapult_trigger = 1
        if isBtnJustPressed("kb:f"):
            if catapult_trigger != 1 and catapult_trigger != -1:
                catapult_trigger = 1
            catapult_trigger *= -1

        gb.write("drive", list(drive))
        gb.write("catapult_trigger", catapult_trigger)

        # print(drive)
        # print("feedback", gb.read("feedback"))

        worker.spin()
