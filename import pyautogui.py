import pyautogui
import time
import random

while True:
    x = random.randint(100, 500)
    y = random.randint(100, 500)
    pyautogui.moveTo(x, y, duration=0.5)
    time.sleep(1)
