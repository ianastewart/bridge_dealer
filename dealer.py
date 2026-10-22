import time

import cv2

from camera import Camera, PI, camera_test

if PI:
    import RPi.GPIO as GPIO
    from mechanics import (
        reset,
        motor_on,
        motor_off,
        feed_card,
        feed_reset,
        board_present,
    )
else:
    from mock_mechanics import (
        reset,
        motor_on,
        feed_card,
        feed_reset,
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
    last_slot = None
    debug = False
    
    def __init__(self, debug=False):
        self.pack = None
        self.card = ""
        self.dealt = {}
        self.suiter = {"C": "S", "D": "E", "H": "W", "S": "N"}
        self.camera = Camera()
        self.camera.debug = debug
        self.debug = debug

    def reset(self):
        self.last_slot = None
        reset()

    def is_ready(self):
        if PI:
            reset()
            feed_reset()
            self.camera.capture()
            tries = 0
            if not self.camera.read_card():
                while True:
                    print("No card")
                    self.camera.show_image()
                    keyed = input("r to retry, q to quit")
                    if keyed == "q":
                        return False
                    if keyed =="r":
                        self.camera.capture()
                        ready = self.camera.read_card()
                        if ready:
                            keyed = input("c to continue, q to quit")
                            if keyed == "q":
                                return False
                            break
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
        self.last_slot = None
        if self.is_ready():
            for r in range(52):
                print(
                    f"Card number {r+1}",
                )
                if not self.deal_card():
                    print("Deal failure")
                    self.camera.show_image()
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
            self.show_debug_images()
            return False
        self.last_slot = feed_card(slot, camera=self.camera, last_slot=self.last_slot)
        if self.last_slot is not None:
            self.dealt[slot].append(self.card)
            self.dealt["All"].append(self.card)
            return True
        print(f"Feed failure {self.card}")
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

    def show_debug_images(self):
        try:
            cv2.imshow("Rank", self.camera.rank_image)
            cv2.imshow("Suit", self.camera.suit_image)
        except Exception as e:
            print("Debug cannot show image", e)

def suits():
    # pack = suit_sorter()
    dealer = Dealer()
    dealer.deal()
