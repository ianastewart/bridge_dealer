import cv2, time
PI = True
try:
    from picamera2 import Picamera2
except ImportError:
    PI = False


# Crop positions
X1 = 230
X2 = 400
Y1 = 20
Y2 = 400
THRESHOLD = 160

PIN_LAMP = 16

# Dimensions of binary masks
WIDTH = 110
SUIT_HEIGHT = 130
RANK_HEIGHT = 190

class Camera:
    picam2 = None
    image = None
    suit_image = None
    rank_image = None
    debug = 0
    error = ""

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
        contours, hierarchy = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        bounds = [cv2.boundingRect(contour) for contour in contours]
        # Sort by largest area
        bounds = sorted(bounds, key=lambda x: x[2] * x[3], reverse=True)
        if self.debug:
            colours = [(255, 0, 0), (0, 255, 0), (0, 0, 255)]
            for i, b in enumerate(bounds):
                colour = colours[i] if i <= 2 else (255, 255, 0)
                source = cv2.rectangle(source, (b[0], b[1]), (b[0] + b[2], b[1] + b[3]), colour, 2)
            cv2.imshow("Contours", source)
        self.rank_image = None
        self.suit_image = None
        if len(bounds) >= 2:
            rank = self.crop_bounds(binary, bounds[0])
            suit = self.crop_bounds(binary, bounds[1])
        else:
            self.error = "Contours < 2"
            return False
        if len(bounds) < 10: # tolerate small unexpected contours
            for i, b in enumerate(bounds):
                if i > 1:
                    # Handle rank = 10 which has two contours
                    # Look for a boundary with similar Y and similar h to the largest boundary
                    # and extend the largest boundary to include it
                    if abs(b[1] - bounds[0][1]) < 10 and abs(b[3] - bounds[0][3]) < 10:
                        rank = binary[bounds[0][1]:bounds[0][1] + bounds[0][3], b[0]: bounds[0][0] + bounds[0][2]]
                        break
        else:
            self.error = "Contours > 4"
            return False
        self.rank_image = cv2.resize(rank, (WIDTH, RANK_HEIGHT))
        self.suit_image = cv2.resize(suit, (WIDTH, SUIT_HEIGHT))
        if self.debug:
            cv2.imshow("Rank", self.rank_image)
            cv2.imshow("Suit", self.suit_image)
            #cv2.waitKey()
        return True

    @staticmethod
    def crop_bounds(image, b):
        # crop image to boundary
        return image[b[1]:b[1] + b[3], b[0]:b[0] + b[2]]

    def stop(self):
        if self.picam2:
            self.picam2.stop()

camera = Camera()

    