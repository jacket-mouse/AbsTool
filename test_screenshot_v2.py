import cv2
import numpy as np
from uiautomator2 import connect

device = connect()
print("Taking screenshot with screencap -p directly...")
try:
    png_bytes = device.shell("screencap -p").output
    image_array = np.frombuffer(png_bytes, dtype=np.uint8)
    img = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
    if img is not None:
        print("Success, shape:", img.shape)
    else:
        print("Got None")
except Exception as e:
    print("Error:", e)
