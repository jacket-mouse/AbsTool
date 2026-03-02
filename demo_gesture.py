import cv2
import numpy as np
import time
from uiautomator2 import connect

print("Connecting to device...")
try:
    device = connect()
    print("Device connected successfully:", device.serial)
except Exception as e:
    print(f"Device connection failed: {e}")
    exit(1)

try:
    print("Testing gesture unlock with OpenCV...")
    device.screen_on()
    print("Swiping up to open lock screen...")
    device.swipe_ext("up", scale=0.8)
    time.sleep(1.5)

    print("Capturing screenshot for OpenCV analysis...")
    image = device.screenshot(format='opencv')
    height, width = image.shape[:2]

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.medianBlur(gray, 7)

    print("Running HoughCircles to detect UI dots...")
    circles = cv2.HoughCircles(
        blurred,
        cv2.HOUGH_GRADIENT,
        dp=1.2,
        minDist=width // 6, # 宫格间距预期
        param1=50,
        param2=25, 
        minRadius=int(width * 0.02),
        maxRadius=int(width * 0.1)
    )

    found_with_cv = False
    x_c, y_c = [], []

    if circles is not None:
        circles = np.round(circles[0, :]).astype("int")
        # 过滤掉非屏幕中下部的干扰圆
        valid_circles = [c for c in circles if c[1] > height * 0.3]
        
        if len(valid_circles) >= 5: # 九宫格可能因为壁纸对比度问题不一定找全，但找到一半就足够推算边界
            print(f"OpenCV detected {len(valid_circles)} pattern dots.")
            xs = [c[0] for c in valid_circles]
            ys = [c[1] for c in valid_circles]
            
            left, right = min(xs), max(xs)
            top, bottom = min(ys), max(ys)
            w = right - left
            h = bottom - top
            
            # 校验九宫格形状大致成正方形，且宽度超过屏幕一定比例
            if 0.7 < w / h < 1.3 and w > width * 0.4:
                print(f"OpenCV successfully resolved pattern bounds: Left={left}, Top={top}, Right={right}, Bottom={bottom}")
                x_c = [left, left + w//2, right]
                y_c = [top, top + h//2, bottom]
                found_with_cv = True

    if not found_with_cv:
        print("OpenCV could not confidently find pattern dots. Falling back to native UI node...")
        pattern_view = device(classNameMatches="(?i).*LockPatternView.*")
        if pattern_view.exists:
            bounds = pattern_view.info['bounds']
            left, top, right, bottom = bounds['left'], bounds['top'], bounds['right'], bounds['bottom']
            w = right - left
            h = bottom - top
            x_c = [left + w/6, left + w/2, left + w*5/6]
            y_c = [top + h/6, top + h/2, top + h*5/6]
        else:
            print("Fallback to generic proportions.")
            x_c = [width*0.2, width*0.5, width*0.8]
            y_c = [height*0.55, height*0.7, height*0.85]
    
    # 手势为 0->1->2->5->8
    pattern = [0, 1, 2, 5, 8]
    points = []
    print(f"Decoding pattern: {pattern}")
    for idx in pattern:
        row = int(idx) // 3
        col = int(idx) % 3
        points.append((x_c[col], y_c[row]))
        
    if points:
        print(f"Resolved points to swipe: {points}")
        device.swipe_points(points, 0.05)
        print("Swipe execution completed.")
        
except Exception as e:
    print(f"Execution failed: {e}")

