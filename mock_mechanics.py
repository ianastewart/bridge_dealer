# Mock the mechanism functions used by Dealer
import time

motor = False


def reset():
    global motor
    motor = False
    state()


def motor_on():
    global motor
    motor = True
    state()


def motor_off():
    global motor
    motor = False
    state()


def feed_card(slot="N", camera=None, last_slot=None, debug=False):
    if camera:
        camera.next()
    return slot


def feed_reset(duration=0.1):
    time.sleep(duration)


def state():
    global motor
    print(f"Motor: {motor}")
    return motor


def board_present():
    return True
