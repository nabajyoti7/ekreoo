import time

patterns = ["10106527", "0323101", "04545011", "1545100", "1455111", "054500000"]

while True:
    for p in patterns:
        print("\r" + p * 20, end="")  # repeat pattern across screen
        time.sleep(0.2)
