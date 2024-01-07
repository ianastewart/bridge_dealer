import time

try:
    import RPi.GPIO as GPIO
except ImportError:
    import Mock.GPIO as GPIO


LAMP_PIN = 16
CARD_FED_PIN = 18
MOTOR_PIN = 35  # Relay 1
EAST_PIN = 33  # Relay 2
WEST_PIN = 31  # Relay 3
SOUTH_PIN = 29  # Relay 4
FEED_PIN = 22  # External relay

FEED_PULSE = 0.05
DELAY_BASE = 0.4
DELAY_INCREMENT = 0.3

RANK = "A23456789TJQK"
SUIT = "CDHS"


def configure_gpio():
    GPIO.setmode(GPIO.BOARD)
    GPIO.setwarnings(False)
    GPIO.setup(MOTOR_PIN, GPIO.OUT)
    GPIO.setup(EAST_PIN, GPIO.OUT)
    GPIO.setup(WEST_PIN, GPIO.OUT)
    GPIO.setup(SOUTH_PIN, GPIO.OUT)
    GPIO.setup(FEED_PIN, GPIO.OUT)
    GPIO.setup(LAMP_PIN, GPIO.OUT)
    GPIO.setup(CARD_FED_PIN, GPIO.IN)


def reset():
    configure_gpio()
    GPIO.output(SOUTH_PIN, GPIO.LOW)
    GPIO.output(WEST_PIN, GPIO.LOW)
    GPIO.output(EAST_PIN, GPIO.LOW)
    GPIO.output(MOTOR_PIN, GPIO.LOW)
    GPIO.output(FEED_PIN, GPIO.LOW)
    GPIO.output(LAMP_PIN, GPIO.LOW)


def set_south():
    GPIO.output(SOUTH_PIN, GPIO.HIGH)
    GPIO.output(WEST_PIN, GPIO.LOW)
    GPIO.output(EAST_PIN, GPIO.LOW)


def set_west():
    GPIO.output(SOUTH_PIN, GPIO.LOW)
    GPIO.output(WEST_PIN, GPIO.HIGH)
    GPIO.output(EAST_PIN, GPIO.LOW)


def set_east():
    GPIO.output(SOUTH_PIN, GPIO.LOW)
    GPIO.output(WEST_PIN, GPIO.LOW)
    GPIO.output(EAST_PIN, GPIO.HIGH)


def set_north():
    GPIO.output(SOUTH_PIN, GPIO.LOW)
    GPIO.output(WEST_PIN, GPIO.LOW)
    GPIO.output(EAST_PIN, GPIO.LOW)


def motor_on():
    GPIO.output(MOTOR_PIN, GPIO.HIGH)


def motor_off():
    GPIO.output(MOTOR_PIN, GPIO.LOW)


def lamp_on():
    GPIO.output(LAMP_PIN, GPIO.HIGH)


def lamp_off():
    GPIO.output(LAMP_PIN, GPIO.LOW)


def is_fed():
    return GPIO.input(CARD_FED_PIN) == 0


def feed(delay=1, cam=None):
    GPIO.output(FEED_PIN, GPIO.HIGH)
    t = 0
    while not is_fed():
        time.sleep(0.01)
        t += 1
        if t == 50:
            GPIO.output(FEED_PIN, GPIO.LOW)
            return False
    if cam:
        time.sleep(0.05)
        cam.capture()
    time.sleep(FEED_PULSE)
    GPIO.output(FEED_PIN, GPIO.LOW)
    time.sleep(delay)
    return True


def feed_card(slot="N", cam=None):
    if slot == "S":
        set_south()
        delay = DELAY_BASE
    elif slot == "W":
        set_west()
        delay = DELAY_BASE + DELAY_INCREMENT
    elif slot == "E":
        set_east()
        delay = DELAY_BASE + 2 * DELAY_INCREMENT
    elif slot == "N":
        set_north()
        delay = DELAY_BASE + 3 * DELAY_INCREMENT
    if feed(delay, cam=cam):
        return True
    print("Feed_error - retrying")
    if feed(delay, cam=None):
        return True
    print("Feed error - Stopped for key")
    input()


def feed_pack(count=13):
    reset()
    motor_on()
    for i in range(count):
        feed_card("N")
        feed_card("E")
        feed_card("W")
        feed_card("S")
    reset()


def gate_test():
    reset()
    t = 0.2
    while True:
        set_south()
        time.sleep(t)
        set_west()
        time.sleep(t)
        set_east()
        time.sleep(t)
