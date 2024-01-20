import cv2
PI = True
try:
    from picamera2 import Picamera2
except ImportError:
    PI = False


# Crop positions
X1 = 235
X2 = 400
Y1 = 20
Y2 = 420
RANK_Y1 = 0
RANK_Y2 = 230
SUIT_Y1 = 225
SUIT_Y2 = 400
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
            if self.debug == 1:
                cv2.imshow("Image", self.image)
                cv2.waitkey(1)
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
        self.rank_image = self.process(suit=False)
        if self.rank_image is None or self.suit_image is None:
            return False
        return True

    def stop(self):
        if self.picam2:
            self.picam2.stop()

def crop_bounds(image, b):
    return image[b[1]:b[1]+b[3], b[0]:b[0]+b[2]]

from mechanics import reset, lamp_on
lamp_on()
cam = Camera()
while True:
    cam.capture()
    #cv2.imshow("Camera", cam.image)   
    source = cam.image[Y1:Y2, X1:X2].copy()
    cv2.imshow("source", source)
    gray = cv2.cvtColor(source, cv2.COLOR_BGR2GRAY)
    k = cv2.waitKey(1)
    threshold = 160
    _, binary = cv2.threshold(gray, threshold, 255, cv2.THRESH_BINARY_INV)
    cv2.imshow("Binary", binary)
#   k = cv2.waitKey()
#     if k == ord("u"):
#         threshold += 5
#     elif k == ord("d"):
#         threshold -= 5
#     elif k == ord("q"):
#         break
#     print(threshold)
    contours, hierarchy = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE) 
    print("Contours", len(contours))
    bounds = [cv2.boundingRect(contour) for contour in contours]
    bounds = sorted(bounds, key = lambda x: x[2] * x[3], reverse=True)
    colours = [(255,0,0), (0,255, 0), (0,0,255)]
    for i, b in enumerate(bounds):
        colour = colours[i] if i <= 2 else (255,255,0) 
        source = cv2.rectangle(source, (b[0], b[1]), (b[0]+b[2], b[1]+b[3]), colour, 2)        
    cv2.imshow("Contours", source)
    #cv2.waitKey()
    rank = None
    suit = None
    if len(bounds) >= 2:
        rank = crop_bounds(binary, bounds[0])
        suit = crop_bounds(binary, bounds[1])
    else:
        #return False
        raise ValueError("Contours")
    if len(bounds) > 2:
        for i , b in enumerate(bounds):
            if i > 1:
                # Hamdle rank = 10
                # look for a boundary with similar Y and similar h to largest boundary
                # and extend largest boundary to include it
                if abs(b[1] - bounds[0][1]) < 10 and abs(b[3] - bounds[0][3]) < 10:
                    rank = binary[bounds[0][1]:bounds[0][1] + bounds[0][3], b[0]: bounds[0][0] + bounds[0][2]]
                    break                                       
#     rank = cv2.resize(rank, (WIDTH, RANK_HEIGHT))
#     suit = cv2.resize(suit, (WIDTH, SUIT_HEIGHT))
    cv2.imshow("Rank", rank)
    cv2.imshow("Suit", suit)
    k = cv2.waitKey()
    if k == ord("q"):
        break

    