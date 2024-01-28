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
GATE_1 = 29
GATE_2 = 31
GATE_3 = 33
INPUT_1 = 40
INPUT_2 = 38


FEED_PULSE = 0.05
DELAY_BASE = 0.2

DELAY_INCREMENT = 0.15

RANK = "A23456789TJQK"
SUIT = "CDHS"


def configure_gpio():
    GPIO.setmode(GPIO.BOARD)
    GPIO.setwarnings(False)
    GPIO.setup(MOTOR_PIN, GPIO.OUT)
    GPIO.setup(GATE_1, GPIO.OUT)
    GPIO.setup(GATE_2, GPIO.OUT)
    GPIO.setup(GATE_3, GPIO.OUT)
    GPIO.setup(INPUT_1, GPIO.OUT)
    GPIO.setup(INPUT_2, GPIO.OUT)
    GPIO.setup(FEED_PIN, GPIO.OUT)
    GPIO.setup(LAMP_PIN, GPIO.OUT)
    GPIO.setup(CARD_FED_PIN, GPIO.IN)


def reset():
    configure_gpio()
    GPIO.output(GATE_1, GPIO.LOW)
    GPIO.output(GATE_2, GPIO.LOW)
    GPIO.output(GATE_3, GPIO.LOW)
    GPIO.output(INPUT_1, GPIO.LOW)
    GPIO.output(INPUT_2, GPIO.LOW)
    GPIO.output(MOTOR_PIN, GPIO.LOW)
    GPIO.output(FEED_PIN, GPIO.LOW)
    GPIO.output(LAMP_PIN, GPIO.LOW)

class Gate():
    def __init__(self, gate_number):
        match gate_number:
            case 1:
                self.pin = GATE_1
            case 2:
                self.pin = GATE_2
            case 3:
                self.pin = GATE_3
        
    def close(self):
        GPIO.output(self.pin, GPIO.HIGH)
        
    def open(self):
        GPIO.output(self.pin, GPIO.LOW)
        
    def is_closed(self):
        return GPIO.input(self.pin) == 1

reset()
south_gate = Gate(1)
west_gate = Gate(2)
east_gate = Gate(3)


def set_south():
    south_gate.close()
    west_gate.open()
    east_gate.open()
 

def set_west():
    west_gate.close()
    south_gate.open()
    east_gate.open()


def set_east():
    east_gate.close()
    south_gate.open()
    west_gate.open()


def set_north():
    east_gate.open()
    south_gate.open()
    west_gate.open()


def feed_forward():
    GPIO.output(INPUT_2, GPIO.HIGH)
    GPIO.output(INPUT_1, GPIO.LOW)

def feed_backwards():
    GPIO.output(INPUT_1, GPIO.HIGH)
    GPIO.output(INPUT_2, GPIO.LOW)

def feed_stop():
    GPIO.output(INPUT_1, GPIO.LOW)
    GPIO.output(INPUT_2, GPIO.LOW)
    
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


def feed_reset(duration=0.05):
    feed_backwards()
    time.sleep(duration)
    feed_stop()



def feed(delay=1, camera=None):
    feed_forward()
    t1 = 0
    while not is_fed():
        time.sleep(0.01) 
        t1 += 1
        if t1 == 100:
            feed_stop()
            return False
    start = time.time()
    if camera:
        time.sleep(0.05)
        camera.capture()
    time.sleep(FEED_PULSE)
    feed_stop()
    t2 = 0
    while is_fed():
        time.sleep(0.01)
        t2 += 1
        if t2 == 50:
            return False
    #print(time.time() - start)
    time.sleep(delay)
    #print(t1, t2)
    return True


def feed_card(slot="N", camera=None):
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
    if feed(delay, camera=camera):
        return True
    print("Feed_error - retrying")
    feed_reset(duration=0.2)
    if feed(delay, camera=None):
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
    t = 0.1
    while True:
        set_south()
        time.sleep(t)
        set_west()
        time.sleep(t)
        set_east()
        time.sleep(t)

def time_path():
    reset()
    motor_on()
    start_time = time.time()
    for i in range(13):
        feed_card("S")
    print (time.time()-start_time)
    reset()
    