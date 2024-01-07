import os
import cv2
import numpy as np
import time
from dataclasses import dataclass

RANK_DIFF_MAX = 6000
SUIT_DIFF_MAX = 4000
IMG_PATH = os.path.dirname(os.path.abspath(__file__)) + "/images/"


@dataclass
class Template:
    image: np.ndarray
    name: str
    score: int


class Matcher:
    rank_templates = []
    suit_templates = []
    debug = False

    def __init__(self):
        """Load the suit and rank templates"""
        for rank in "23456789TJQKA":
            image = cv2.imread(f"{IMG_PATH}{rank}.png", cv2.IMREAD_GRAYSCALE)
            self.rank_templates.append(Template(image=image, name=rank, score=0))
        for suit in "CDHS":
            image = cv2.imread(f"{IMG_PATH}{suit}.png", cv2.IMREAD_GRAYSCALE)
            self.suit_templates.append(Template(image=image, name=suit, score=0))

    def match(self, rank_image: np.ndarray, suit_image: np.ndarray):
        """
        Finds best rank and suit matches for the image.
        Difference the query card rank and suit images with the template rank and suit images.
        The best match is the rank or suit image that has the least difference.
        """
        best_rank_score = 10000
        best_suit_score = 10000
        best_rank_template = None
        best_suit_template = None
        rank_template = None
        suit_template = None
        # Difference the query card rank image from each of the train rank images,
        # and store the result with the least difference
        for template in self.rank_templates:
            diff_img = cv2.absdiff(rank_image, template.image)
            template.score = int(np.sum(diff_img) / 255)
            if template.score < best_rank_score:
                best_rank_score = template.score
                best_rank_template = template

            # Same process with suit images
        for template in self.suit_templates:
            diff_img = cv2.absdiff(suit_image, template.image)
            template.score = int(np.sum(diff_img) / 255)
            if template.score < best_suit_score:
                best_suit_score = template.score
                best_suit_template = template

        if best_rank_score < RANK_DIFF_MAX:
            rank_template = best_rank_template

        if best_suit_score < SUIT_DIFF_MAX:
            suit_template = best_suit_template

        return rank_template, suit_template

    def debug(self):
        for template in self.rank_templates:
            print(template.name, template.score)
        for template in self.suit_templates:
            print(template.name, template.score)


def match_test():
    start = time.time()
    m = Matcher()
    ace = cv2.imread(f"{IMG_PATH}2.png", cv2.IMREAD_GRAYSCALE)
    spade = cv2.imread(f"{IMG_PATH}C.png", cv2.IMREAD_GRAYSCALE)
    rank_template, suit_template = m.match(ace, spade)
    print(f"{rank_template.name}{suit_template.name}")
    m.debug()
    end = time.time()
    print("Elapsed", end - start)
