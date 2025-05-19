# Mock the mechanism functions used by Dealer
import time

motor = False
lamp = False


def reset():
    global motor, lamp
    motor = False
    lamp = False
    state()


def motor_on():
    global motor, lamp
    motor = True
    state()


def motor_off():
    global motor
    motor = False
    state()


def feed_card(slot="N", camera=None):
    if camera:
        camera.next()
    return True


def feed_reset(duration=0.1):
    time.sleep(duration)


def lamp_on():
    global lamp
    lamp = True
    state()


def state():
    global motor, lamp
    print(f"Motor: {motor} Lamp: {lamp}")
    return motor, lamp


def board_present():
    return True
