import ctypes
import time
import random

# Harmless prank: shows random funny messages
messages = [
    "Error 404: Motivation not found!",
    "Installing VIRUS.EXE... Just kidding.",
    "Your PC will self-destruct in 5 seconds... maybe.",
    "Blue Screen of Happiness!",
    "Relax, it's just a prank :)"
]

for i in range(1000000000000000000):  # show 10 popups
    msg = random.choice(messages)
    ctypes.windll.user32.MessageBoxW(0, msg, "Windows Alert", 1)
    time.sleep(1)
