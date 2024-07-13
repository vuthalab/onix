import numpy as np 
import matplotlib.pyplot as plt
from onix.headers.quarto_monitor import Quarto
import time

q = Quarto()

data_time = q.data_time()

b_x = []

start_time = time.time()
while True:
    try:
        current_time = time.time()
        if current_time - start_time >= data_time:
            b_x.append(np.mean(q.data()))
        start_time = current_time
    except KeyboardInterrupt:
        print(b_x) # save the data when you close this
