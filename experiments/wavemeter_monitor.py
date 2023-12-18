import time

import numpy as np
from onix.data_tools import save_experiment_data
from onix.units import ureg

from onix.data_tools import save_persistent_data

from onix.headers.wavemeter.wavemeter import WM
import matplotlib.pyplot as plt
import sys

from tqdm import tqdm

wavemeter = WM()

def wavemeter_frequency():
    freq = wavemeter.read_frequency(5)
    if isinstance(freq, str):
        return -1
    return freq


##

def save_data():
    data = {
        "times": times,
        "frequencies": frequencies
    }
    name = "Wavemeter"
    data_id = save_persistent_data(name, data)
    print(data_id)

##

frequencies = []
times = []

total_time = 48 * 60 # minutes
measurement_period = 5 # min

measurements = int(total_time / measurement_period)

for i in tqdm(range(measurements)):
    frequencies.append(round(wavemeter_frequency(), 3))
    times.append(time.time())

    time.sleep(measurement_period * 60)

save_data()
