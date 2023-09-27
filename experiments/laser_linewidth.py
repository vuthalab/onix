import matplotlib.pyplot as plt
import numpy as np
import time
from onix.data_tools import save_experiment_data

from onix.headers.wavemeter.wavemeter import WM
from onix.headers.quarto import Quarto
import matplotlib.pyplot as plt

wavemeter = WM()
qu = Quarto()

def wavemeter_frequency():
    freq = wavemeter.read_frequency(params["wm_channel"])
    if isinstance(freq, str):
        return -1
    return freq

## Parameters
params = {
    "wm_channel": 5,
    "n_avg" : 10,
}

## Get error signal data
V_errs = []

N_avgs = params["n_avg"]

for i in range(N_avgs):
    V_errs.append(qu.get_errdata())
    time.sleep(1)

## Save Data
data = {
    "V_errs": V_errs,
}
headers = {
    "params": params,
    "wavemeter_frequency": wavemeter_frequency(),
    "resolution" : 2e-6,
}

name = "Laserlock Error"
data_id = save_experiment_data(name, data, headers)
print(data_id)
