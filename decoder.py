import os
import cv2
import numpy as np

X1 = 200
X2 = 380
Y1 = 20
Y2 = 390

THRESHOLD = 130


# Dimensions of binary masks
WIDTH = 110
SUIT_HEIGHT = 130
RANK_HEIGHT = 190

def show():
    img_path = os.path.dirname(os.path.abspath(__file__)) + f"/raw/"
    while True:
        name = input("Name: ")
        if name == "q":
            break
        image = cv2.imread(f"{img_path}{name}.png")
        decode_image(image)
        cv2.imshow("Image", image)
        cv2.waitKey(0)
        

def decode_image(image, debug=True):
    suit_image = None
    rank_image = None
    threshold = THRESHOLD
    source = image[Y1:Y2, X1:X2].copy()
    gray = cv2.cvtColor(source, cv2.COLOR_BGR2GRAY)
    _, binary = cv2.threshold(gray, threshold, 255, cv2.THRESH_BINARY_INV)
    contours, hierarchy = cv2.findContours(
        binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )
    bounds_all = [cv2.boundingRect(contour) for contour in contours]
    bounds_filtered = filter(lambda x: 1 < x[0] < 100, bounds_all)
    # Sort by largest area
    bounds = sorted(bounds_filtered, key=lambda x: x[2] * x[3], reverse=True)
    if debug:
        colours = [(255, 0, 0), (0, 255, 0), (0, 0, 255)]
        for i, b in enumerate(bounds):
            colour = colours[i] if i <= 2 else (255, 255, 0)
            # print(f"Bounds {i} = {b}")
            source = cv2.rectangle(
                source, (b[0], b[1]), (b[0] + b[2], b[1] + b[3]), colour, 2
            )
        cv2.imshow("Contours", source)
        cv2.imshow("Binary", binary)
        cv2.waitKey(1)
    rank_image = None
    suit_image = None       
    if len(bounds) >= 2:
        rank = crop_bounds(binary, bounds[0])
        suit = crop_bounds(binary, bounds[1])
    else:
        error = "Contours < 2"
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
        error = "Contours > 4"
        return False
    rank_bounds = bounds[0]
    suit_bounds = bounds[1]
    rank_image = cv2.resize(rank, (WIDTH, RANK_HEIGHT))
    suit_image = cv2.resize(suit, (WIDTH, SUIT_HEIGHT))
    if debug:
        cv2.imshow("Rank", rank_image)
        cv2.imshow("Suit", suit_image)
        cv2.waitKey(1)
    return True

def crop_bounds(image, b):
    # crop image to boundary
    return image[b[1] : b[1] + b[3], b[0] : b[0] + b[2]]

img_path = os.path.dirname(os.path.abspath(__file__)) + f"/raw/"
image = cv2.imread(f"{img_path}redC3.png")
decode_image(image)
   