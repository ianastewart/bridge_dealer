import time

import cv2

from camera import camera
from matcher import Matcher
from mechanics import reset, motor_on, motor_off, feed_card, feed_reset, lamp_on

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
        self.matcher = Matcher()
        self.pack = None
        self.dealt = []
        camera.debug=True

    def is_ready(self):
        reset()
        lamp_on()
        camera.capture()
        tries = 0
        while not camera.read_card():
            time.sleep(0.5)
            camera.capture()
            tries += 1
            print("No card")
            if tries == 100:
                return False
        return True

    def deal(self, pack=None):
        if pack:
            self.pack = pack
        if self.pack is None:
            raise ValueError("No pack to deal")
        self.dealt = []
        if self.is_ready():
            motor_on()
            for r in range(52 - len(self.dealt)):
                print(f"{52 - len(self.dealt)} cards remaining")
                feed_reset(duration=.05)
                camera.capture()
                retries = 0
                while not self.next_card():
                    print("Rewind")
                    feed_reset(duration=.1)
                    camera.capture()
                    retries += 1
                    if retries > 5:
                        raise ValueError("Card retries exceeded")
#                 while not camera.read_card():
#                     feed_reset(duration=.1)
#                     camera.capture()
#                     resets += 1
#                     print(f"{reset} resets")
#                     if resets > 10:
#                         reset()
#                         raise ValueError("Card cannot be read")
# 
#                 rank_template, suit_template = self.matcher.match(
#                     camera.rank_image, camera.suit_image
#                 )
#                 rank = rank_template.name if rank_template else "?"
#                 suit = suit_template.name if suit_template else "X"
#                 card = f"{rank}{suit}"
                if self.card in self.dealt:
                    self.debug()
                    print(f"Card {self.card} has already been dealt")
                    reset()
                    return
                if self.card in self.pack:
                    slot = self.pack[self.card][0]
                    print("Card", self.card, slot)
                    feed_card(slot, camera=None)
                    self.dealt.append(self.card)
                else:
                    print(f"Bad card: {self.card}")
                    self.matcher.debug()
                    self.debug()
                    reset()
                    return
            reset()
            
    def next_card(self):
        """
        Read captured image and decode into self.card"
        Return True if successful
        """
        self.card = "--"
        camera.read_card()
        rank_template, suit_template = self.matcher.match(
            camera.rank_image, camera.suit_image
        )
        rank = rank_template.name if rank_template else "?"
        suit = suit_template.name if suit_template else "X"
        self.card = f"{rank}{suit}"
        if "?" in self.card or "X" in self.card:
            return False
        return True

    def debug(self):
        cv2.imshow("Rank", camera.rank_image)
        cv2.imshow("Suit", camera.suit_image)
        cv2.waitKey(5)


def camera_test():
    lamp_on()
    time.sleep(2)
    motor_on()
    camera.capture()
    while True:
        camera.read_card()
        # cv2.imshow("Input", camera.image)
        cv2.imshow("Rank", camera.rank_image)
        cv2.imshow("Suit", camera.suit_image)
        k = cv2.waitKey(1)
        if k == ord("q"):
            reset()
            break
        if k == ord("f"):
            feed_card("N", camera)
        camera.capture()


# 
# pack = suit_sorter()
# dealer = Dealer()
# dealer.deal(pack)
