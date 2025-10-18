import random
import time
import os

# Terminal size (adjust for your screen)
width = 80
height = 20

# Create empty screen
screen = [" " * width for _ in range(height)]

while True:
    # Pick random column
    col = random.randint(0, width - 1)
    
    # Add a random binary digit at the top
    char = random.choice(["0", "1"])
    screen[0] = screen[0][:col] + char + screen[0][col + 1:]
    
    # Move screen down (like falling)
    screen = [screen[0]] + screen[:-1]
    
    # Clear and print
    os.system("cls" if os.name == "nt" else "clear")
    for row in screen:
        print(row)
    
    time.sleep(0.005)
