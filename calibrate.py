import cv2
import os
import glob
import time
from camera import camera
from mechanics import reset, motor_on, lamp_on, feed_card, feed_reset


def calibrate(name="images2"):
    """
    Reads 4 cards with suits in sequence C D H S to South slot
    Then 13 cards in order of rank 2 to A to West slot
    """
    img_path = os.path.dirname(os.path.abspath(__file__)) + f"/{name}/"
    clear_dir(name)

    suit = "CDHS"
    rank = "23456789TJQKA"

    reset()
    lamp_on()
    camera.debug = False
    time.sleep(2)
    motor_on()
    feed_reset()
    for s in suit:
        camera.capture()
        camera.read_card()
        file = img_path + f"{s}.png"
        cv2.imwrite(file, camera.suit_image)
        feed_card("S")

    for r in rank:
        camera.capture()
        camera.read_card()
        file = img_path + f"{r}.png"
        cv2.imwrite(file, camera.rank_image)
        feed_card("W")
    time.sleep(1)
    reset()


def clear_dir(name="images"):
    img_path = os.path.dirname(os.path.abspath(__file__)) + f"/{name}/"
    files = glob.glob(img_path + "*.*")
    for f in files:
        try:
            os.unlink(f)
        except OSError as e:
            print(f"Error: {f}, {e.strerror}")


def camera_test():
    camera.debug = True
    reset()
    lamp_on()
    if camera.is_ready():
        while True:
            camera.capture()
            camera.read_card()


#     #         cv2.imshow("Input", cam.image)
#             cv2.imshow("Rank", cam.rank_image)
#             cv2.imshow("Suit", cam.suit_image)
#             k = cv2.waitKey(1)
# #         if k == ord("q"):
#             break
#         if k == ord("f"):
#             feed_card("N", cam)
#     reset()

images = []


# calibrate()
def capture_raw():
    name = input("Name")
    img_path = os.path.dirname(os.path.abspath(__file__)) + f"/raw/"
    # clear_dir("raw")
    reset()
    motor_on()
    lamp_on()
    time.sleep(1)
    for r in range(13):
        camera.capture()
        file = f"{img_path}{name}{r}.png"
        cv2.imwrite(file, camera.image)
        feed_card("S")
    reset()


def show():
    img_path = os.path.dirname(os.path.abspath(__file__)) + f"/raw/"
    while True:
        name = input("Name: ")
        image = cv2.imread(f"{img_path}{name}.png", cv2.IMREAD_GRAYSCALE)
        cv2.imshow(name, image)
        cv2.waitKey(1)
