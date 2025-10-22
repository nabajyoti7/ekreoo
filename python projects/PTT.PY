import time

n = 0
while True:
    print(bin(n)[2:])  # convert number to binary, remove '0b'
    n += 1
    time.sleep(0.000001)   # delay so it doesn’t scroll too fast
