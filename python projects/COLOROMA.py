import random, time, os
from colorama import Fore, Style, init

init()

width = 80
height = 20
screen = [" " * width for _ in range(height)]

while True:
    col = random.randint(0, width - 1)
    char = random.choice(["0", "1"])
    screen[0] = screen[0][:col] + Fore.GREEN + char + Style.RESET_ALL + screen[0][col+1:]
    screen = [screen[0]] + screen[:-1]

    os.system("cls" if os.name == "nt" else "clear")
    for row in screen:
        print(row)
    
    time.sleep(0.05)
