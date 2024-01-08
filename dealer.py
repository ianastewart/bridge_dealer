import time

import cv2

from camera import Camera
from matcher import Matcher
from mechanics import reset, motor_on, motor_off, feed_card, lamp_on

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
        self.camera = Camera()
        self.matcher = Matcher()
        self.pack = None
        self.dealt = []

    def is_ready(self):
        reset()
        lamp_on()
        self.camera.capture()
        self.camera.process()
        tries = 0
        while not self.camera.read_card():
            time.sleep(0.5)
            self.camera.capture()
            tries += 1
            print("No card")
            if tries == 100:
                return False
        return True

    def deal(self, pack=None):
        lamp_on()
        if pack:
            self.pack = pack
        if self.pack is None:
            raise ValueError("No pack to deal")
        
        if self.is_ready():
            motor_on()
            for r in range(52 - len(self.dealt)):
                print(f"{52 - len(self.dealt)} cards remaining")
                self.camera.read_card()
                rank_template, suit_template = self.matcher.match(
                    self.camera.rank_image, self.camera.suit_image
                )
                rank = rank_template.name if rank_template else "?"
                suit = suit_template.name if suit_template else "X"
                card = f"{rank}{suit}"
                if card in self.dealt:
                    self.debug()
                    print(f"Card {card} has already been dealt")
                    reset()
                    return
                if card in self.pack:
                    slot = self.pack[card][0]
                    feed_card(slot, self.camera)
                    self.dealt.append(card)
                else:
                    print(f"Bad card: {card}")
                    self.matcher.debug()
                    self.debug()
                    reset()
                    return
            reset()

    def debug(self):
        cv2.imshow("Rank", self.camera.rank_image)
        cv2.imshow("Suit", self.camera.suit_image)
        cv2.waitKey(5)


def camera_test():
    cam = Camera()
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

# 
# pack = suit_sorter()
# dealer = Dealer()
# dealer.deal(pack)
