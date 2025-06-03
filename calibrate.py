import cv2
import os
import glob
import time
from camera import camera, PI, Camera

if PI:
    from mechanics import reset, motor_on, lamp_on, feed_card, feed_reset
else:
    from mock_mechanics import reset, motor_on, lamp_on, feed_card, feed_reset


def read_templates(name="images2"):
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
    camera.debug = True
    camera.capture()
    time.sleep(1)
    motor_on()
    for s in suit:
        feed_reset()
        camera.capture()
        if camera.read_card():
            file = img_path + f"{s}.png"
            cv2.imwrite(file, camera.suit_image)
            feed_card("S")
        else:
            print(f"No suit image in {s}.png")
    for r in rank:
        feed_reset()
        camera.capture()
        if camera.read_card():
            file = img_path + f"{r}.png"
            cv2.imwrite(file, camera.rank_image)
            feed_card("W")
        else:
            print("No rank image in {r}.png")
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
    if PI:
        camera.debug = True
        reset()
        lamp_on()
        if camera.is_ready():
            while True:
                camera.capture()
                camera.read_card()
    else:
        print("Function not available")


def capture_raw():
    name = input("Folder name: ")
    img_path = os.path.dirname(os.path.abspath(__file__)) + f"/{name}/"
    if not os.path.exists(img_path):
        os.makedirs(img_path)
    if os.listdir(img_path):
        clear = input("Delete existing files? ").lower()
        if clear in ["yes", "y"]:
            clear_dir("img_path")
    if PI:
        reset()
        lamp_on()
        camera.capture()
        time.sleep(2)
        motor_on()
    camera.capture()
    for r in range(52):
        file = f"{img_path}{r}.png"
        print(file)
        cv2.imshow("Image", camera.image)
        cv2.waitKey(1)
        cv2.imwrite(file, camera.image)
        if r < 13:
            dest = "S"
        elif r < 26:
            dest = "W"
        elif r < 39:
            dest = "E"
        else:
            dest = "N"
        if r == 51:
            break
        if PI:
            # feed card and load next camera image
            feed_card(dest, camera=camera)
        else:
            # just load next image
            camera.next()
    if PI:
        reset()


def show():
    img_path = os.path.dirname(os.path.abspath(__file__)) + "/raw/"
    while True:
        name = input("Name: ")
        image = cv2.imread(f"{img_path}{name}.png", cv2.IMREAD_GRAYSCALE)
        cv2.imshow(name, image)
        cv2.waitKey(1)


if __name__ == "__main__":
    print("0 = Capture 52 raw images to folder")
    print("1 = Read suit and rank for templates")
    print("2 = Show images in folder")
    print("3 = Test camera (PI only)")
    sel = input("Function: ")
    match sel:
        case "0":
            capture_raw()
        case "1":
            read_templates()
        case "2":
            show()
        case "3":
            camera_test()
        case _:
            print("Invalid selection")
else:
    camera = Camera()
