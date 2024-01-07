import cv2
import os
import glob
from camera import Camera
from mechanics import reset, motor_on, feed_card, lamp_on


def calibrate():
    """
    Reads 4 cards with suits in sequence C D H S to South slot
    Then 13 cards in order of rank 2 to A to West slot
    """
    img_path = os.path.dirname(os.path.abspath(__file__)) + "/images/"
    files = glob.glob(img_path + "*.*")
    for f in files:
        try:
            os.unlink(f)
        except OSError as e:
            print(f"Error: {f}, {e.strerror}")

    suit = "CDHS"
    rank = "23456789TJQKA"

    reset()
    motor_on()
    lamp_on()
    for s in suit:
        cam.read_card()
        file = img_path + f"{s}.png"
        cv2.imwrite(file, cam.suit_image)
        feed_card("S")

    for r in rank:
        cam.read_card()
        file = img_path + f"{r}.png"
        cv2.imwrite(file, cam.rank_image)
        feed_card("W")
    reset()


cam = Camera()
calibrate()
