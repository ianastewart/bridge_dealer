import cv2
import time
from camera import Camera
from matcher import Matcher
from mechanics import reset, motor_on, feed_card, lamp_on


RANKS = "23456789TJQKA"
SUITS = "CDHS"


def make_pack():
    pack = {}
    for s in SUITS:
        for r in RANKS:
            pack[r + s] = None
    return pack


def suit_sorter():
    pack = {}
    slots = {"C": "S", "D": "W", "H": "E", "S": "N"}
    for s in SUITS:
        for r in RANKS:
            pack[r + s] = (slots[s], False)
    return pack


def deal(pack):
    global cam, matcher
    reset()
    motor_on()
    lamp_on()
    time.sleep(0.5)
    cam.capture()
    for r in range(52):
        cam.read_card()
        rank_template, suit_template = matcher.match(cam.rank_image, cam.suit_image)
        rank = rank_template.name if rank_template else "?"
        suit = suit_template.name if suit_template else "X"
        card = f"{rank}{suit}"
        if card in pack:
            slot = pack[card][0]
            feed_card(slot, cam)
            pack[card][1] = True
        else:
            print(f"Bad card: {card}")
            matcher.debug()
            cv2.imshow("Rank", cam.rank_image)
            cv2.imshow("Suit", cam.suit_image)
            cv2.waitKey(1)
            return
    reset()


def camera_test():
    global cam
    reset()
    lamp_on()
    motor_on()
    time.sleep(0.5)
    cam.capture()
    while True:
        cam.read_card()
        cv2.imshow("R", cam.rank_image)
        cv2.imshow("S", cam.suit_image)
        k = cv2.waitKey(1)
        if k == ord("q"):
            break
        if k == ord("f"):
            feed_card("N", cam)
    reset()


cam = Camera()
matcher = Matcher()
pack = suit_sorter()
deal(pack)
