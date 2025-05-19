from pathlib import Path
import cv2
from camera import Camera


def test_read():
    folder_name = "red"
    folder = Path(__file__).parent.parent.joinpath("rawimages", folder_name)
    for f in folder.iterdir():
        img = cv2.imread(f, cv2.IMREAD_GRAYSCALE)
        cv2.imshow("Image", img)
        cv2.waitKey(50)


def test_camera_init():
    cam = Camera()
    cam.debug = False
    assert len(cam.rank_templates) == 13
    assert len(cam.suit_templates) == 4
    while True:
        cam.capture()
        cv2.imshow("Image", cam.image)
        cam.read_card()
        cv2.imshow("Rank image", cam.rank_image)
        cv2.imshow("Suit image", cam.suit_image)
        cv2.waitKey(0)
        cam.next()
