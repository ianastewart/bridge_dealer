import cv2
import os
import glob
import time
from camera import Camera
from mechanics import reset, motor_on, lamp_on, feed_on, feed_off, is_fed



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
images = []
#calibrate()
def capture_stream():
    reset()
    motor_on()
    lamp_on()
    time.sleep(1)
    while True:
        feed_on()
        t1 = 0
        while not is_fed():
            cam.capture()
            images.append(cam.image) 
            t1 += 1
            time.sleep(0.005)
            if t1 == 100:
                return
        cam.capture()
        images.append(cam.image)
        feed_off()
        print(len(images))
        k = input()
        if k == "q":
            return
        show()


def show():
    for i in range(len(images)):
        cv2.imshow(str(i), images[i])
        cv2.waitKey(1)
    