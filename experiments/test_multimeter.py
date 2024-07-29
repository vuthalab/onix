from onix.headers.RigolDM3068 import DM3068
import time
import matplotlib.pyplot as plt

d = DM3068()

data = []
t = []

try:
    while True:
        t_start = time.time()
        data.append(d.get_voltage())
        t.append(time.time_ns())
        t_end = time.time()
        print(f"Data point took {t_end - t_start}")
except KeyboardInterrupt:
    if len(data) != len(t):
        t.append(time.time_ns())
    print(data)
    plt.plot(t, data)
    plt.show()
