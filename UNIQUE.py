import random
import time

heroes = ["a young warrior", "an old wizard", "a lost traveler", "a clever thief", "a brave child"]
villains = ["a shadow king", "a fire dragon", "a corrupted priest", "a dark machine", "a cruel tyrant"]
places = ["in the frozen north", "beyond the desert", "deep under the sea", "in the floating city", "at the edge of time"]
treasures = ["the crystal of dawn", "the crown of storms", "the book of infinity", "the blade of silence", "the heart of stars"]
twists = [
    "but the treasure was alive",
    "yet the villain was their father",
    "and the hero was already dead",
    "but time looped back to the beginning",
    "yet the world itself was an illusion"
]

def slow_print(text, delay=0.05):
    for ch in text:
        print(ch, end="", flush=True)
        time.sleep(delay)
    print()

def generate_story():
    hero = random.choice(heroes)
    villain = random.choice(villains)
    place = random.choice(places)
    treasure = random.choice(treasures)
    twist = random.choice(twists)

    slow_print(f"Once upon a time, {hero} began a journey {place}.")
    time.sleep(1)
    slow_print(f"They sought {treasure}, guarded by {villain}.")
    time.sleep(1)
    slow_print(f"Battles were fought, choices were made, destinies were broken...")
    time.sleep(1.5)
    slow_print(f"In the end, {twist}.")
    time.sleep(1.5)
    slow_print("The story fades... but another will rise.\n")

print("📖 Generating a random story...\n")
generate_story()
