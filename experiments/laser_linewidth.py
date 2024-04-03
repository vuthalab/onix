import matplotlib.pyplot as plt
import numpy as np
import time
from onix.data_tools import save_experiment_data

from onix.headers.wavemeter.wavemeter import WM
from onix.headers.quarto_frequency_lock import Quarto
from onix.headers.pcie_digitizer.pcie_digitizer import Digitizer
import matplotlib.pyplot as plt
from onix.analysis.laser_linewidth import LaserLinewidth
from onix.analysis.power_spectrum import PowerSpectrum


from onix.experiments.shared import m4i

discriminator_slope = 1.5e-5
laser = LaserLinewidth(2000, 2e-6, discriminator_slope)
spec = PowerSpectrum(2000, 2e-6)

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
    for i in range(N_avgs):
        err_data = q.get_cavity_error_data(2000)
        V_errs.append(err_data)
        laser.add_data(err_data)
        spec.add_data(err_data)
    print(f"Laser Linewidth is {laser.linewidth} Hz")
## Power Spectrum Plots
fig, ax = plt.subplots()

ax.plot(spec.f, spec.power_spectrum)
ax.set_xscale("log")
ax.set_yscale("log")
ax.set_xlabel("Frequency (Hz)")
ax.set_ylabel(r"Power Spectral Density (V$^2$ / Hz)")
ax.set_title("Laser Unlocked Power Spectral Density")
ax.grid()
plt.show()
## Laser Linewidth Plots
fig, (ax1, ax2, ax3) = plt.subplots(1,3)

ax1.plot(laser.f, laser.W_nu)
ax1.set_xscale("log")
ax1.set_yscale("log")
ax1.set_xlabel("Frequency (Hz)")
ax1.set_ylabel(r"Frequency Noise Spectral Density (Hz$^2$ / Hz)")
ax1.set_title("Frequency Noise Spectral Density")
ax1.grid()

ax2.plot(laser.f, laser.W_phi)
ax2.set_xscale("log")
ax2.set_yscale("log")
ax2.set_xlabel("Frequency (Hz)")
ax2.set_ylabel(r"Phase Noise Spectral Density (1/Hz)")
ax2.set_title("Phase Noise Spectral Density")
ax2.grid()

ax3.plot(laser.f, laser.W_phi_integral)
ax3.plot(laser.f, np.ones(len(laser.f))*(1/np.pi), color = "Black")
ax3.set_xscale("log")
ax3.set_yscale("log")
ax3.set_xlabel("Frequency (Hz)")
ax3.set_ylabel(r"Cumulated Phase Noise")
ax3.set_title("Cumulated Phase Noise")
ax3.grid()
plt.tight_layout()
plt.show()

## Manually Perform a Power Spectrum



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


