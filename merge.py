# Merge two sets of template images
import cv2
from pathlib import Path


base_path = Path(__file__).parent
template1 = "images"
template2 = "images2"
output = "merged"
for rank in "23456789TJQKA":
    file1 = base_path.joinpath(template1, f"{rank}.png")
    image1 = cv2.imread(file1, cv2.IMREAD_GRAYSCALE)
    file2 = base_path.joinpath(template2, f"{rank}.png")
    image2 = cv2.imread(file2, cv2.IMREAD_GRAYSCALE)
    result = cv2.bitwise_or(image1, image2)
    cv2.imwrite(base_path.joinpath("merged", f"{rank}.png"), result)

for suit in "CDHS":
    file1 = base_path.joinpath(template1, f"{suit}.png")
    image1 = cv2.imread(file1, cv2.IMREAD_GRAYSCALE)
    file2 = base_path.joinpath(template2, f"{suit}.png")
    image2 = cv2.imread(file2, cv2.IMREAD_GRAYSCALE)
    result = cv2.bitwise_or(image1, image2)
    cv2.imwrite(base_path.joinpath("merged", f"{suit}.png"), result)

