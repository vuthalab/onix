import matplotlib.pyplot as plt
import numpy as np
import time
from onix.data_tools import save_experiment_data

from onix.headers.wavemeter.wavemeter import WM
from onix.headers.quarto_frequency_lock import Quarto
from onix.headers.pcie_digitizer.pcie_digitizer import Digitizer
import matplotlib.pyplot as plt
from onix.analysis.laser_linewidth import LaserLinewidth


from onix.experiments.shared import m4i

discriminator_slope = 1.5e-5
laser = LaserLinewidth(2000, 2e-6, discriminator_slope, 2000)

wavemeter = WM()

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
if params["source"] == "quarto":
    q = Quarto("/dev/ttyACM1")
    resolution = 2e-6
    for i in range(N_avgs):
        err_data = q.get_cavity_error_data(2000)
        V_errs.append(err_data)
        laser.add_data(err_data)
    print(f"Laser Linewidth is {laser.linewidth} Hz")

##
fig, ax = plt.subplots()

ax.plot(laser.f, laser.W_nu)
ax.set_xscale("log")
ax.set_yscale("log")
ax.set_xlabel("Frequency (Hz)")
ax.set_ylabel(r"Frequency Noise Spectral Density (Hz$^2$ / Hz)")
ax.set_title("Frequency Noise Spectral Density")
ax.grid()
plt.show()

##
fig, ax = plt.subplots()
ax.plot(laser.f, laser.W_phi)
ax.set_xscale("log")
ax.set_yscale("log")
ax.set_xlabel("Frequency (Hz)")
ax.set_ylabel(r"Phase Noise Spectral Density (1/Hz)")
ax.set_title("Phase Noise Spectral Density")
ax.grid()
plt.show()

##
fig, ax = plt.subplots()
ax.plot(laser.f, laser.W_phi_integral)
ax.set_xscale("log")
ax.set_yscale("log")
ax.set_xlabel("Frequency (Hz)")
ax.set_ylabel(r"Cumulated Phase Noise")
ax.set_title("Cumulated Phase Noise")
ax.grid()
plt.show()

## Save Data
data = {
    "V_errs": V_errs,
}
headers = {
    "params": params,
    "wavemeter_frequency": wavemeter_frequency(),
    "resolution" : resolution,
}

name = "Laserlock Error"
data_id = save_experiment_data(name, data, headers)
print(data_id)


