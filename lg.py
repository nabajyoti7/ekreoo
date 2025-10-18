import random
import time
import os
import math
from colorama import Fore, Style, init

# Initialize colors
init(autoreset=True)

# Define a palette of ASCII symbols to create visual patterns
PALETTE = ["@", "#", "&", "%", "$", "*", "+", "=", "-", ":", ".", " ","5","2","3","Chandra GAy"]

# Colors to spice things up
COLORS = [
    Fore.RED, Fore.GREEN, Fore.YELLOW,
    Fore.BLUE, Fore.MAGENTA, Fore.CYAN, Fore.WHITE
]

# Screen size
WIDTH = 80
HEIGHT = 30

def clear():
    os.system("cls" if os.name == "nt" else "clear")

def random_char():
    return random.choice(PALETTE)

def random_color():
    return random.choice(COLORS)

def generate_pattern():
    """Generate a random ASCII pattern as a 2D grid"""
    grid = []
    for y in range(HEIGHT):
        row = []
        for x in range(WIDTH):
            char = random_char()
            row.append(char)
        grid.append(row)
    return grid

def distort(grid, level=3):
    """Distort grid like waves or fractal ripples"""
    distorted = [[cell for cell in row] for row in grid]
    for _ in range(level):
        x_shift = random.randint(-2, 2)
        y_shift = random.randint(-2, 2)
        for y in range(HEIGHT):
            for x in range(WIDTH):
                ny = (y + y_shift) % HEIGHT
                nx = (x + x_shift) % WIDTH
                distorted[y][x] = grid[ny][nx]
    return distorted

def print_grid(grid, colorful=True):
    """Render the grid beautifully"""
    for row in grid:
        line = ""
        for cell in row:
            if colorful:
                line += random_color() + cell
            else:
                line += cell
        print(line)

def mandala_effect(iterations=10):
    """Generate shifting mandala-like patterns"""
    grid = generate_pattern()
    for i in range(iterations):
        clear()
        distorted = distort(grid, level=random.randint(1, 5))
        print_grid(distorted)
        time.sleep(0.2)
        grid = distorted

def spiral_effect(turns=5):
    """Draw an ASCII spiral with math"""
    clear()
    spiral = [[" " for _ in range(WIDTH)] for _ in range(HEIGHT)]
    cx, cy = WIDTH // 2, HEIGHT // 2
    angle = 0
    radius = 1
    for _ in range(turns * 200):
        x = int(cx + math.cos(angle) * radius)
        y = int(cy + math.sin(angle) * radius)
        if 0 <= x < WIDTH and 0 <= y < HEIGHT:
            spiral[y][x] = random.choice(PALETTE[:6])
        angle += 0.1
        radius += 0.02
    print_grid(spiral)

def rain_effect(frames=50):
    """Matrix-style falling rain of characters"""
    cols = [0] * WIDTH
    for _ in range(frames):
        clear()
        screen = [[" " for _ in range(WIDTH)] for _ in range(HEIGHT)]
        for i in range(WIDTH):
            if random.random() < 0.2:
                cols[i] = 0
            char = random.choice(PALETTE)
            y = cols[i] % HEIGHT
            screen[y][i] = char
            cols[i] += 1
        print_grid(screen)
        time.sleep(0.1)

def main_show():
    """Mix all effects into a creative infinite loop"""
    while True:
        mandala_effect(iterations=15)
        spiral_effect(turns=6)
        rain_effect(frames=40)

if __name__ == "__main__":
    try:
        main_show()
    except KeyboardInterrupt:
        clear()
        print(Style.BRIGHT + Fore.CYAN + "\nGoodbye, Creator 🌌✨\n")
