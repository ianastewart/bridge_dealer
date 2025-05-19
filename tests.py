import cv2
import os
import glob
from time import sleep
from camera import Camera, PI

if PI:
    from mechanics import reset, motor_on, feed_card, lamp_on
else:
    from mock_mechanics import reset, motor_on, feed_card, lamp_on


def feed_pack(count=13):
    reset()
    motor_on()
    for i in range(count):
        feed_card("N")
        feed_card("E")
        feed_card("W")
        feed_card("S")
    reset()


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


def test_match():
    cam = Camera(mock_source="green2")
    cam.debug = True
    number = 0
    while number < 52:
        number += 1
        cam.capture()
        success = cam.read_card()
        if success:
            card = cam.match()
            print(number, card)
        else:
            print(number, cam.error)
            break
        sleep(0.3)

    # iter = cam.base_path.joinpath("rawimages", inputs).iterdir()
    # while True:
    #     image=cv2.imread(iter.__next__(), cv2.IMREAD_COLOR_BGR)
    #     cv2.imshow("Image", image)
    #     cv2.waitKey(1)


cam = Camera()
test_match()
