import math
import time
import os

width, height = os.get_terminal_size()

theta = 0.0
try:
    while True:
        os.system("cls" if os.name == "nt" else "clear")

        for y in range(height):
            for x in range(width):
                # Convert x, y to polar coordinates
                dx = x - width / 2
                dy = y - height / 2
                r = math.sqrt(dx*dx + dy*dy)
                angle = math.atan2(dy, dx)

                # Spiral formula
                value = math.sin(r / 3 - theta + angle * 2)

                # Choose characters depending on value
                if value > 0.6:
                    char = "@"
                elif value > 0.2:
                    char = "o"
                elif value > -0.2:
                    char = "."
                else:
                    char = " "

                print(char, end="")
            print()
        theta += 0.2
        time.sleep(0.05)

except KeyboardInterrupt:
    print("\nSpiral animation ended.")
