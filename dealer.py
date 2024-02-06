import time

import cv2

from camera import camera
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
        self.pack = None
        self.card = ""
        self.dealt = []
        self.suiter = {"C":"S", "D":"E", "H":"W", "S":"N"}
        self.camera = camera
        camera.debug = True

    def is_ready(self):
        reset()
        lamp_on()
        time.sleep(0.5)
        feed_reset()
        camera.capture()
        tries = 0
        while not camera.read_card():
            time.sleep(0.5)
            camera.capture()
            tries += 1
            print("No card")
            if tries == 100:
                return False
        print("Ready")
        return True

    def deal(self, pack=None):
        if pack:
            self.pack = pack
        self.dealt = []
        if self.is_ready():
            for r in range(52 - len(self.dealt)):
                print(f"{52 - len(self.dealt)} cards remaining")
                if not self.deal_card():
                    print("Deal failure")
                    self.debug()
                    reset()
                    return False
            reset()
            return True
        print("Not ready")

    def deal_card(self):
        """ Deal next card from the pack """
        motor_on()
        #feed_reset(duration=0.05)
        #camera.capture()
        retries = 0
        while not self.next_card():
            print("Rewind")
            feed_reset(duration=0.1)
            camera.capture()
            retries += 1
            if retries > 5:
                return False
        if self.pack:
            # Use a preset deal
            try:
                slot = self.pack[self.card][0]
            except KeyError:
                print(f"Bad card: {self.card}")
                return False
        else:
            # Deal into suits
            try:
                slot = self.suiter[self.card[1]]
            except KeyError:
                print(f"Bad card: {self.card}")
                return False
        print("Card", self.card, slot)
        if self.card in self.dealt:
            print(f"Card {self.card} already dealt")
            return False
        if feed_card(slot, camera=camera):
            self.dealt.append(self.card)
            return True
        print("Feed failure {self.card}")
        return False


    def next_card(self):
        """
        Read captured image and decode into self.card"
        Return True if successful
        """
        if camera.read_card():
            self.card = camera.match()
            if "?" in self.card:
                return False
            return True
        return False

    def debug(self):
        cv2.imshow("Rank", camera.rank_image)
        cv2.imshow("Suit", camera.suit_image)
        cv2.waitKey(5)

#
# pack = suit_sorter()
# dealer = Dealer()
# dealer.deal(pack)
