import os
import cv2
import numpy as np
import time
from dataclasses import dataclass

PI = True
try:
    from picamera2 import Picamera2
except ImportError:
    PI = False


# Crop positions to extract top left of card
X1 = 230
X2 = 400
Y1 = 20
Y2 = 400

THRESHOLD = 160

# Dimensions of binary masks
WIDTH = 110
SUIT_HEIGHT = 130
RANK_HEIGHT = 190

RANK_DIFF_MAX = 7000
SUIT_DIFF_MAX = 4000
IMG_PATH = os.path.dirname(os.path.abspath(__file__)) + "/images/"


@dataclass
class Template:
    image: np.ndarray
    name: str
    score: int


class Camera:
    picam2 = None
    image = None
    suit_image = None
    rank_image = None
    rank_templates = []
    suit_templates = []
    debug = 0
    error = ""

    def __init__(self):
        if PI:
            self.picam2 = Picamera2()
            self.picam2.preview_configuration.main.size = (640, 480)
            self.picam2.preview_configuration.main.format = "RGB888"
            self.picam2.set_controls({"Contrast": 8})
            self.picam2.start()
        for rank in "23456789TJQKA":
            image = cv2.imread(f"{IMG_PATH}{rank}.png", cv2.IMREAD_GRAYSCALE)
            self.rank_templates.append(Template(image=image, name=rank, score=0))
        for suit in "CDHS":
            image = cv2.imread(f"{IMG_PATH}{suit}.png", cv2.IMREAD_GRAYSCALE)
            self.suit_templates.append(Template(image=image, name=suit, score=0))

    def capture(self):
        if PI:
            self.image = self.picam2.capture_array()
        else:
            self.image = None
        self.suit_image = None
        self.rank_image = None

    def is_ready(self):
        self.capture()
        tries = 0
        while not self.read_card():
            time.sleep(0.1)
            self.capture()
            tries += 1
            if tries == 100:
                return False
            print("Tries", tries)
        return True

    def read_card(self):
        self.suit_image = None
        self.rank_image = None
        if self.image is None:
            self.error = "No image"
            return False
        source = self.image[Y1:Y2, X1:X2].copy()
        gray = cv2.cvtColor(source, cv2.COLOR_BGR2GRAY)
        _, binary = cv2.threshold(gray, THRESHOLD, 255, cv2.THRESH_BINARY_INV)
        contours, hierarchy = cv2.findContours(
            binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        bounds = [cv2.boundingRect(contour) for contour in contours]
        # Sort by largest area
        bounds = sorted(bounds, key=lambda x: x[2] * x[3], reverse=True)
        if self.debug:
            print("Bounds 0", bounds[0], "Bounds 1", bounds[1])
            colours = [(255, 0, 0), (0, 255, 0), (0, 0, 255)]
            for i, b in enumerate(bounds):
                colour = colours[i] if i <= 2 else (255, 255, 0)
                source = cv2.rectangle(
                    source, (b[0], b[1]), (b[0] + b[2], b[1] + b[3]), colour, 2
                )
            cv2.imshow("Contours", source)
        self.rank_image = None
        self.suit_image = None
        if len(bounds) >= 2:
            rank = self.crop_bounds(binary, bounds[0])
            suit = self.crop_bounds(binary, bounds[1])
        else:
            self.error = "Contours < 2"
            return False
        if len(bounds) < 10:  # tolerate small unexpected contours
            for i, b in enumerate(bounds):
                if i > 1:
                    # Handle rank = 10 which has two contours
                    # Look for a boundary with similar Y and similar h to the largest boundary
                    # and extend the largest boundary to include it
                    if abs(b[1] - bounds[0][1]) < 10 and abs(b[3] - bounds[0][3]) < 10:
                        rank = binary[
                            bounds[0][1] : bounds[0][1] + bounds[0][3],
                            b[0] : bounds[0][0] + bounds[0][2],
                        ]
                        break
        else:
            self.error = "Contours > 4"
            return False
        self.rank_image = cv2.resize(rank, (WIDTH, RANK_HEIGHT))
        self.suit_image = cv2.resize(suit, (WIDTH, SUIT_HEIGHT))
        if self.debug:
            cv2.imshow("Rank", self.rank_image)
            cv2.imshow("Suit", self.suit_image)
            cv2.waitKey()
        return True

    def match(self):
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
            diff_img = cv2.absdiff(self.rank_image, template.image)
            template.score = int(np.sum(diff_img) / 255)
            if template.score < best_rank_score:
                best_rank_score = template.score
                best_rank_template = template

            # Same process with suit images
        for template in self.suit_templates:
            diff_img = cv2.absdiff(self.suit_image, template.image)
            template.score = int(np.sum(diff_img) / 255)
            if template.score < best_suit_score:
                best_suit_score = template.score
                best_suit_template = template

        if best_rank_score < RANK_DIFF_MAX:
            rank_template = best_rank_template

        if best_suit_score < SUIT_DIFF_MAX:
            suit_template = best_suit_template

        return rank_template, suit_template

    @staticmethod
    def crop_bounds(image, b):
        # crop image to boundary
        return image[b[1] : b[1] + b[3], b[0] : b[0] + b[2]]

    def stop(self):
        if self.picam2:
            self.picam2.stop()


camera = Camera()
