import matplotlib.pyplot as plt
import numpy as np
import time
from onix.data_tools import save_experiment_data

from onix.headers.wavemeter.wavemeter import WM
from onix.headers.quarto_frequency_lock import Quarto
import matplotlib.pyplot as plt
from onix.analysis.power_spectrum import PowerSpectrum

wavemeter = WM()

noise = PowerSpectrum(num_of_samples=2000, time_resolution=2e-6, max_points_per_decade=1e6)

def wavemeter_frequency():
    freq = wavemeter.read_frequency(params["wm_channel"])
    if isinstance(freq, str):
        return -1
    return freq

## Parameters
params = {
    "wm_channel": 5,
    "n_avg" : 1000,
    "source": "quarto"
}

## Get error signal data
V_errs = []
N_avgs = params["n_avg"]

q = Quarto("/dev/ttyACM5")
resolution = 2e-6
for i in range(N_avgs):
    #err_data = q.get_cavity_error_data(2000)
    output = q.get_output_data(2000)
    V_errs.append(output)
    noise.add_data(output)

##
fig, ax = plt.subplots()
ax.plot(noise.f, noise.power_spectrum)
ax.set_xscale("log")
ax.set_yscale("log")
ax.set_xlabel("Frequency (Hz)")
text = "Power Spectrum $\\mathrm{V}^2 / \\mathrm{Hz}$"
ax.set_ylabel(text)
ax.set_title("Power Spectrum")
ax.grid()
plt.tight_layout()
plt.show()


## Save Data
data = {
    "Output": V_errs,
}
headers = {
    "params": params,
    "wavemeter_frequency": wavemeter_frequency(),
    "resolution" : resolution,
}

name = "Laser Lock System Noise"
data_id = save_experiment_data(name, data, headers)
print(data_id)


