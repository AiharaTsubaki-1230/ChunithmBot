import cv2

image = cv2.imread('./src/chunithm/bg_lmnp.png')

blur = cv2.blur(image, (100, 100))

cv2.imwrite("./src/chunithm/background.png", blur)