import numpy as np
import matplotlib.pyplot as plt
import os
import pandas as pd
from onix.analysis.fitter import Fitter
from scipy.signal import find_peaks

# os.chdir("/home/icarus/Documents/data/manual/2024_02/19/")
# data = pd.read_csv("cavity_oscilloscope_data.csv")
# params = pd.read_csv("cavity_oscilloscope_params.txt")

os.chdir("C:\\Users\\bassa\\Desktop")
data = pd.read_csv("data.csv")
params = pd.read_csv("params.txt")

reflection = data.loc[:, "CH1"].to_numpy()[1:].astype(np.float64)
error = data.loc[:, "CH3"].to_numpy()[1:].astype(np.float64)
transmission = data.loc[:, "CH4"].to_numpy()[1:].astype(np.float64)

time_start = data.loc[:, "Start"].to_numpy()[0].astype(np.float64)
time_increment = data.loc[:, "Increment"].to_numpy()[0].astype(np.float64)
time = np.arange(time_start, time_start + time_increment*len(reflection), time_increment)


peaks, _ = find_peaks(transmission, height=1e-3)
time_peak = time[peaks]
transmission_peak = transmission[peaks]
transmission_peak = transmission_peak[time_peak > 0]
time_peak = time_peak[time_peak > 0]

def decay(t, A, tau, c):
    return A * np.exp(-t/tau) + c
fitter = Fitter(decay)
fitter.set_absolute_sigma(False)
fitter.set_data(time_peak, transmission_peak)
fitter.set_p0({"tau": 8e-6})
fitter.fit()
fit_times = np.linspace(5e-6, max(time), 100)

fig, ax = plt.subplots()
# ax.plot(time, reflection, label="reflection")
ax.plot(time, error, label="error")
ax.plot(time, transmission, label="transmission")
ax.plot(time_peak, transmission_peak, 'x', color = "C2")
ax.plot(fit_times, fitter.fitted_value(fit_times), label = "envelope decay fit", color = "C2")

results = fitter.results
errors = fitter.errors
ax.text(min(time), max(transmission), r"fit $y = Ae^{-t/\tau} + c$")
for i, (label, value) in enumerate(results.items()):
    if label == "tau":
        slash = "\\"
    else:
        slash = ""
    ax.text(min(time), max(transmission) - (max(transmission)-min(transmission))/10 * (i+1), f"${slash}{label}$ = {value:.2e}")

plt.xlabel("time (s)")
plt.ylabel("detector amplitude (V)")
plt.legend()
plt.show()