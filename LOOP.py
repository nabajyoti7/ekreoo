import os
import random
import time

# Terminal size
width, height = os.get_terminal_size()

# Aquarium objects
fish_types = [
    "<><", "><>", "><((°>", "><(((°>", "><>=", "<°)))><", ">°)))><", "><>"
]
seaweed_chars = ["|", "/", "\\"]
bubble_char = "o"

# Seaweed positions
seaweed = [random.randint(0, width - 1) for _ in range(width // 10)]

# Fish list (x, y, direction, sprite)
fish = [
    [random.randint(0, width - 1),
     random.randint(0, height - 1),
     random.choice([-1, 1]),
     random.choice(fish_types)]
    for _ in range(8)
]

# Bubbles (x, y)
bubbles = []

def draw_aquarium():
    screen = [[" " for _ in range(width)] for _ in range(height)]

    # Place seaweed at bottom
    for x in seaweed:
        for y in range(height - 5, height):
            screen[y][x] = random.choice(seaweed_chars)

    # Place fish
    for f in fish:
        x, y, d, sprite = f
        if 0 <= y < height:
            if d == 1:  # facing right
                for i, ch in enumerate(sprite):
                    if 0 <= x + i < width:
                        screen[y][x + i] = ch
            else:  # facing left
                reversed_sprite = sprite[::-1]
                for i, ch in enumerate(reversed_sprite):
                    if 0 <= x - i < width:
                        screen[y][x - i] = ch

    # Place bubbles
    for bx, by in bubbles:
        if 0 <= bx < width and 0 <= by < height:
            screen[by][bx] = bubble_char

    # Print aquarium
    os.system("cls" if os.name == "nt" else "clear")
    for row in screen:
        print("".join(row))

def update_positions():
    # Move fish
    for f in fish:
        f[0] += f[2]
        # Bounce if out of screen
        if f[0] <= 0:
            f[2] = 1
        elif f[0] >= width - len(f[3]):
            f[2] = -1

        # Random vertical drift
        if random.random() < 0.1:
            f[1] += random.choice([-1, 1])
            f[1] = max(0, min(height - 1, f[1]))

    # Move bubbles
    for i in range(len(bubbles)):
        bx, by = bubbles[i]
        bubbles[i] = (bx + random.choice([-1, 0, 1]), by - 1)
    # Remove bubbles out of screen
    bubbles[:] = [(bx, by) for bx, by in bubbles if by >= 0]

    # Occasionally add a new bubble
    if random.random() < 0.3:
        bubbles.append((random.randint(0, width - 1), height - 1))

# Main loop
try:
    while True:
        draw_aquarium()
        update_positions()
        time.sleep(0.1)
except KeyboardInterrupt:
    print("\nAquarium closed.")
