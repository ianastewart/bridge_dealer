import time

try:
    import RPi.GPIO as GPIO
except ImportError:
    print("No RPi.GPIO")

# Output pins
MOTOR = 35  # Relay 1
GATE_1 = 29 # Relay 4
GATE_2 = 31 # Relay 3
GATE_3 = 33 # Relay 2
DRIVER_1 = 40 # Feed motor driver
DRIVER_2 = 38 # Feed motor driver
# Input pins
CARD_FED = 32 #18
BOARD_SWITCH = 36

# Time in seconds after card detected as fed
FEED_PULSE = 0.1
WAIT_BASE = 0.2
WAIT_INCREMENT = 0
FEED_RETRIES = 5
# Global vars
ready_time = 0
last_slot = ""


def wait_until_ready():
    """ Wait until last fed card has passed its gate """
    global ready_time
    if ready_time > 0:
        t = 0
        while time.time() < ready_time:
            time.sleep(0.01)
            t += 1
        print(f"Waited {t*10} ms")


def configure_gpio():
    GPIO.setmode(GPIO.BOARD)
    GPIO.setwarnings(False)
    GPIO.setup(MOTOR, GPIO.OUT)
    GPIO.setup(GATE_1, GPIO.OUT)
    GPIO.setup(GATE_2, GPIO.OUT)
    GPIO.setup(GATE_3, GPIO.OUT)
    GPIO.setup(DRIVER_1, GPIO.OUT)
    GPIO.setup(DRIVER_2, GPIO.OUT)
    #
    GPIO.setup(CARD_FED, GPIO.IN)
    GPIO.setup(BOARD_SWITCH, GPIO.IN, pull_up_down=GPIO.PUD_UP)


def reset():
    read_time = 0
    wait_until_ready()
    configure_gpio()
    GPIO.output(GATE_1, GPIO.LOW)
    GPIO.output(GATE_2, GPIO.LOW)
    GPIO.output(GATE_3, GPIO.LOW)
    GPIO.output(DRIVER_1, GPIO.LOW)
    GPIO.output(DRIVER_2, GPIO.LOW)
    GPIO.output(MOTOR, GPIO.LOW)


class Gate:
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
    GPIO.output(DRIVER_2, GPIO.HIGH)
    GPIO.output(DRIVER_1, GPIO.LOW)


def feed_backwards():
    GPIO.output(DRIVER_1, GPIO.HIGH)
    GPIO.output(DRIVER_2, GPIO.LOW)


def feed_stop():
    GPIO.output(DRIVER_1, GPIO.LOW)
    GPIO.output(DRIVER_2, GPIO.LOW)


def motor_on():
    GPIO.output(MOTOR, GPIO.HIGH)


def motor_off():
    GPIO.output(MOTOR, GPIO.LOW)


def is_fed():
    return GPIO.input(CARD_FED) == 0


def feed_reset(duration=0.1):
    feed_backwards()
    time.sleep(duration)
    feed_stop()


def feed(camera=None, debug=False):
    feed_forward()
    t1 = 0
    while not is_fed():
        time.sleep(0.01)
        t1 += 1
        if t1 == 500:
            feed_stop()
            return False
    if camera:      
        camera.capture()
    t2 = time.time()
    time.sleep(FEED_PULSE)
    feed_stop()
    t3 = 0
    while is_fed():
        time.sleep(0.01)
        t3 += 1
        if t3 == 100:
            return False
    card_time= int((time.time() - t2)*100)#time.sleep(.1) #added
    if debug:
        print(t1, card_time)
    return True


def feed_card(slot="N", camera=None, last_slot=None, debug=False):
    delay = 0
    if slot == last_slot or last_slot is None:
        pass
        # print("Feed immediately")
    elif last_slot == "N":
        if slot == "S":
            pass
        elif slot == "W":
            delay = WAIT_BASE +  WAIT_INCREMENT
        elif slot == "E":
            delay = WAIT_BASE + 2 * WAIT_INCREMENT
    elif last_slot == "E":
        delay = WAIT_BASE + 2 * WAIT_INCREMENT
    elif last_slot == "W":
        delay = WAIT_BASE + WAIT_INCREMENT
    if delay > 0:    
        time.sleep(delay)
    if slot == "S":
        set_south()
    elif slot == "W":
        set_west()
    elif slot == "E":
        set_east()
    elif slot == "N":
        set_north()
    retry = 0
    if debug:
        print(f"Feed: {slot} last: {last_slot} delay: {delay}")
    while retry < FEED_RETRIES:
        if feed(camera=camera, debug=debug):
            return slot
        retry += 1
        print(f"Feed_error - retrying {retry}")
        feed_reset(duration=0.2)
    print("Fatal feed error")
    motor_off()
    return None

def board_present():
    return GPIO.input(BOARD_SWITCH) == 0 
    
def feed_pack(count=13, reverse=False, mixed=False):
    reset()
    motor_on()
    start = time.time()
    last_slot = None
    for i in range(count):
        print(i)
        if reverse:
            last_slot = feed_card("N", last_slot=last_slot)
            last_slot = feed_card("E", last_slot=last_slot)
            last_slot = feed_card("W", last_slot=last_slot)
            last_slot = feed_card("S", last_slot=last_slot)
        elif mixed:
            last_slot = feed_card("N", last_slot=last_slot)
            last_slot = feed_card("S", last_slot=last_slot)
            last_slot = feed_card("E", last_slot=last_slot)
            last_slot = feed_card("W", last_slot=last_slot)
        else:
            last_slot = feed_card("S", last_slot=last_slot)
            last_slot = feed_card("W", last_slot=last_slot)
            last_slot = feed_card("E", last_slot=last_slot)
            last_slot = feed_card("N", last_slot=last_slot)
    time.sleep(.3)
    end = time.time()
    mode = "Reverse" if reverse else "Mixed" if mixed else "Normal"
    print (f"{mode} run time: {int(end-start)}")
    reset()


def test_fast(count=13):
    reset()
    motor_on()
    start = time.time()
    last_slot=None
    for i in range (count):
        last_slot = feed_card("S", last_slot=last_slot)
    for i in range (count):        
        last_slot = feed_card("W", last_slot=last_slot)
    for i in range(count): 
        last_slot = feed_card("E", last_slot=last_slot)
    for i in range(count):
        last_slot = feed_card("N", last_slot=last_slot)
    time.sleep(.3)
    end = time.time()
    mode = "Fast"
    print (f"{mode} run time: {int(end-start)}")
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
    time.sleep(.2)
    start_time = time.time()
    for i in range(13):
        set_north()
        feed_card("S")
        feed_card("W")
    print(time.time() - start_time)
    reset()
