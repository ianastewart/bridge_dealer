import time

import cv2

from camera import Camera
from matcher import Matcher
from mechanics import reset, motor_on, feed_card, lamp_on

RANKS = "23456789TJQKA"
SUITS = "CDHS"


def suit_sorter():
    sorted_pack = {}
    slots = {"C": "S", "D": "W", "H": "E", "S": "N"}
    for s in SUITS:
        for r in RANKS:
            sorted_pack[r + s] = (slots[s], False)
    return sorted_pack


class Dealer:
    def __init__(self):
        self.pack = None
        self.dealt = []

    def is_ready(self):
        global cam, matcher
        reset()
        lamp_on()
        cam.capture()
        cam.process()
        tries = 0
        while not cam.read_card():
            time.sleep(0.5)
            cam.capture()
            tries += 1
            if tries == 20:
                return False
        return True

    def deal(self, pack):
        if self.is_ready():
            motor_on()
            for r in range(52):
                cam.read_card()
                rank_template, suit_template = matcher.match(
                    cam.rank_image, cam.suit_image
                )
                rank = rank_template.name if rank_template else "?"
                suit = suit_template.name if suit_template else "X"
                card = f"{rank}{suit}"
                if card in self.dealt:
                    self.debug()
                    raise ValueError(f"Card {card} has already been dealt")
                if card in pack:
                    slot = pack[card][0]
                    feed_card(slot, cam)
                    self.dealt.append(card)
                else:
                    print(f"Bad card: {card}")
                    matcher.debug()
                    self.debug()
                    return
            reset()

    def debug(self):
        cv2.imshow("Rank", cam.rank_image)
        cv2.imshow("Suit", cam.suit_image)
        cv2.waitKey(5)


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
