import random
import time
import os

# Characters used for the rain
chars = "01"

# Width of the terminal
width = os.get_terminal_size().columns

# Create drops for each column
drops = [0 for _ in range(width)]

try:
    while True:
        print("".join(
            random.choice(chars) if i % 2 == 0 and drops[i] > 0 else " "
            for i in range(width)
        ))

        # Update drops
        drops = [d+1 if random.random() > 0.975 else 0 for d in drops]

        time.sleep(0.05)

except KeyboardInterrupt:
    print("\nMatrix rain ended.")
