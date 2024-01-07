PI = True
try:
    from picamera2 import Picamera2
except ImportError:
    PI = False
import cv2

# Crop positions
X1 = 180
X2 = 390
RANK_Y1 = 0
RANK_Y2 = 230
SUIT_Y1 = 225
SUIT_Y2 = 390
RANK_THRESHOLD = 180
SUIT_THRESHOLD = 165

PIN_LAMP = 16

# Dimensions of binary masks
WIDTH = 130
SUIT_HEIGHT = 150
RANK_HEIGHT = 210


class Camera:
    picam2 = None
    image = None
    suit_image = None
    rank_image = None
    debug = 0

    def __init__(self):
        if PI:
            self.picam2 = Picamera2()
            self.picam2.preview_configuration.main.size = (640, 480)
            self.picam2.preview_configuration.main.format = "RGB888"
            self.picam2.set_controls({"Contrast": 8})
            self.picam2.start()

    def capture(self):
        if PI:
            self.image = self.picam2.capture_array()
        else:
            self.image = None
        self.suit_image = None
        self.rank_image = None
        return self.image

    def process(self, suit=True):
        if self.image is None:
            return None
        if suit:
            crop = self.image[SUIT_Y1:SUIT_Y2, X1:X2].copy()
            threshold = SUIT_THRESHOLD
            name = "Suit"
        else:
            crop = self.image[RANK_Y1:RANK_Y2, X1:X2].copy()
            threshold = RANK_THRESHOLD
            name = "Rank"
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        _, thresh = cv2.threshold(blur, threshold, 255, cv2.THRESH_BINARY)
        binary = cv2.bitwise_not(thresh)
        if self.debug > 1:
            cv2.imshow(f"{name} gray", gray)
            cv2.imshow(f"{name} thresh", thresh)
        contours, hierarchy = cv2.findContours(
            binary, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE
        )
        if len(contours) > 0:
            cont = max(contours, key=cv2.contourArea)
            x, y, w, h = cv2.boundingRect(cont)
            if suit:
                cropped = binary[y : y + SUIT_HEIGHT, x : x + WIDTH]
                sized = cv2.resize(cropped, (WIDTH, SUIT_HEIGHT))
            else:
                cropped = binary[y : y + RANK_HEIGHT, x : x + WIDTH]
                sized = cv2.resize(cropped, (WIDTH, RANK_HEIGHT))
            if self.debug > 0:
                cv2.imshow(f"{name} binary", sized)
            return sized
        if self.debug > 0:
            k = cv2.waitKey(1)
            if k == ord("q"):
                quit()
        return None

    def read_card(self):
        self.suit_image = self.process(suit=True)
        if self.suit_image is None:
            raise ValueError("No suit image")
        self.rank_image = self.process(suit=False)
        if self.rank_image is None:
            raise ValueError("No rank image")

    def stop(self):
        if self.picam2:
            self.picam2.stop()
