import cv2
import os
import glob
import time
from camera import camera
from mechanics import reset, motor_on, lamp_on, feed_card, feed_reset


def calibrate(name="images"):
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
    camera.debug=False
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
            camera.capture()
            images.append(cam.image) 
            t1 += 1
            time.sleep(0.005)
            if t1 == 100:
                return
        camera.capture()
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
    