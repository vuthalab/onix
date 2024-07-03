# import threading
from onix.headers.quarto_frequency_lock import Quarto
from onix.headers.find_quarto import find_quarto
import time

# class LaserUnlockCheck(Quarto):
#     def __init__(self, address = find_quarto("frequency")[0]): # TODO: double check that this is correct
#         Quarto.__init__(self, address)
#         self.device_lock = threading.Lock()

laser = Quarto(find_quarto("frequency", return_all = True)[0])

while True:
    counter1 = laser.get_unlock_counter()
    print("Running Experiment")
    time.sleep(5)
    counter2 = laser.get_unlock_counter()
    if counter1 == counter2:
        break

print("Experiment complete without unlock")