import os, random, time, sys

# ANSI colors for fireworks
colors = [
    "\033[91m", "\033[92m", "\033[93m",
    "\033[94m", "\033[95m", "\033[96m"
]
reset = "\033[0m"

def clear():
    os.system('cls' if os.name == 'nt' else 'clear')

def firework():
    width = 60
    height = 20
    x = random.randint(10, width - 10)
    y = random.randint(5, height - 5)
    color = random.choice(colors)

    # explosion patterns
    patterns = [
        [" * ",
         "***",
         " * "],

        ["  *  ",
         " *** ",
         "*****",
         " *** ",
         "  *  "],

        ["   *   ",
         "  ***  ",
         " ***** ",
         "*******",
         " ***** ",
         "  ***  ",
         "   *   "]
    ]
    pattern = random.choice(patterns)

    # draw
    for i, row in enumerate(pattern):
        line = " " * (x - len(row)//2) + color + row + reset
        sys.stdout.write("\033[%d;%dH%s" % (y + i, 0, line))
        sys.stdout.flush()
    time.sleep(0.3)

def main():
    try:
        while True:
            clear()
            firework()
            time.sleep(0.5)
    except KeyboardInterrupt:
        clear()
        print("🎆 Fireworks show ended 🎆")

if __name__ == "__main__":
    main()
