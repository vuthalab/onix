# import threading
from onix.headers.quarto_frequency_lock import Quarto
from onix.headers.find_quarto import find_quarto
import time


laser = Quarto(find_quarto("frequency", return_all = True)[0])

while True:
    locked1, counter1 = laser.check_lock(0.3)
    if locked1:
        print("Running Experiment")
        time.sleep(5)
        locked2, counter2 = laser.check_lock(0.3)
        print(counter1, counter2)
        if counter1 == counter2:
            break
        print("Laser unlocked during experiment. Re-running.")
    else:
        print("Laser unlocked. Can't start experiment. Re-trying.")
        time.sleep(1)


print("Experiment complete without unlock")