import time

import cv2

from camera import Camera, PI

if PI:
    import RPi.GPIO as GPIO
    from mechanics import (
        reset,
        motor_on,
        motor_off,
        feed_card,
        feed_reset,
        lamp_on,
        board_present,
    )
else:
    from mock_mechanics import (
        reset,
        motor_on,
        feed_card,
        feed_reset,
        lamp_on,
        board_present,
    )

RANKS = "23456789TJQKA"
SUITS = "CDHS"
DEALT_KEYS = ["All", "N", "E", "S", "W"]


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
        self.dealt = {}
        self.suiter = {"C": "S", "D": "E", "H": "W", "S": "N"}
        self.camera = Camera()
        self.camera.debug = True

    def reset(self):
        reset()

    def is_ready(self):
        if PI:
            reset()
            lamp_on()
            time.sleep(0.5)
            feed_reset()
            self.camera.capture()
            tries = 0
            while not self.camera.read_card():
                time.sleep(0.5)
                self.camera.capture()
                tries += 1
                print("No card")
                if tries == 100:
                    return False
            print("Ready")
            return True
        else:
            return True

    def board_present(self):
        return board_present()

    def deal(self, pack=None):
        if pack:
            self.pack = pack
        for key in DEALT_KEYS:
            self.dealt[key] = []
        if self.is_ready():
            for r in range(52):
                print(
                    f"Card number {r+1}",
                )
                if not self.deal_card():
                    print("Deal failure")
                    self.debug()
                    reset()
                    self.print_dealt()
                    return False
            time.sleep(0.5)
            reset()
            self.print_dealt()
            return True
        print("Not ready")

    def deal_card(self):
        """Deal next card from the pack"""
        motor_on()
        retries = 0
        while not self.next_card():
            print("Rewind")
            feed_reset(duration=0.1)
            self.camera.capture()
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
        print(self.card, slot)
        if self.card in self.dealt["All"]:
            print(f"Card {self.card} already dealt")
            return False
        if feed_card(slot, camera=self.camera):
            self.dealt[slot].append(self.card)
            self.dealt["All"].append(self.card)
            return True
        print("Feed failure {self.card}")
        return False

    def next_card(self):
        """
        Read captured image and decode into self.card"
        Return True if successful
        """
        if self.camera.read_card():
            self.card = self.camera.match()
            if "?" in self.card:
                return False
            return True
        return False

    def print_dealt(self):
        for key in ["All", "N", "E", "S", "W"]:
            print(f"{key}: " + " ".join(self.dealt[key]))

    def debug(self):
        cv2.imshow("Rank", self.camera.rank_image)
        cv2.imshow("Suit", self.camera.suit_image)
        cv2.waitKey(5)


def suits():
    # pack = suit_sorter()
    dealer = Dealer()
    dealer.deal()
