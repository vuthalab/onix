import numpy as np
import matplotlib.pyplot as plt
import os
import pandas as pd
from onix.analysis.fitter import Fitter
from scipy.signal import find_peaks

# os.chdir("/home/icarus/Documents/data/manual/2024_02/19/")
# data = pd.read_csv("cavity_oscilloscope_data.csv")
# params = pd.read_csv("cavity_oscilloscope_params.txt")

# os.chdir("/home/icarus/Documents/data/manual/2024_03/11")
# data = pd.read_csv("data.csv")
# params = pd.read_csv("params.txt")

# #reflection = data.loc[:, "CH1"].to_numpy()[1:].astype(np.float64)
# #error = data.loc[:, "CH3"].to_numpy()[1:].astype(np.float64)
# transmission = data.loc[:, "CH4"].to_numpy()[1:].astype(np.float64)

# time_start = data.loc[:, "Start"].to_numpy()[0].astype(np.float64)
# time_increment = data.loc[:, "Increment"].to_numpy()[0].astype(np.float64)
# time = np.arange(time_start, time_start + time_increment*len(reflection), time_increment)


# peaks, _ = find_peaks(transmission, height=1e-3)
# time_peak = time[peaks]
# transmission_peak = transmission[peaks]
# transmission_peak = transmission_peak[time_peak > 0]
# time_peak = time_peak[time_peak > 0]



# fig, ax = plt.subplots()
# # ax.plot(time, reflection, label="reflection")
# ax.plot(time, error, label="error")
# ax.plot(time, transmission, label="transmission")
# ax.plot(time_peak, transmission_peak, 'x', color = "C2")
# ax.plot(fit_times, fitter.fitted_value(fit_times), label = "envelope decay fit", color = "C2")

# results = fitter.results
# errors = fitter.errors
# ax.text(min(time), max(transmission), r"fit $y = Ae^{-t/\tau} + c$")
# for i, (label, value) in enumerate(results.items()):
#     if label == "tau":
#         slash = "\\"
#     else:
#         slash = ""
#     ax.text(min(time), max(transmission) - (max(transmission)-min(transmission))/10 * (i+1), f"${slash}{label}$ = {value:.2e}")

# plt.xlabel("time (s)")
# plt.ylabel("detector amplitude (V)")
# plt.legend()
# plt.show()

def decay(t, A, tau, c):
    return A * np.exp(-t/tau) + c

class Oscilloscope():
    def __init__(self, data_loc, data_name = "data.csv", params_name = "params.txt"):
        os.chdir(data_loc)
        self.data = pd.read_csv(data_name)
        self.params = pd.read_csv(params_name)

    def get_channel_data(self, channel):
        return self.data.loc[:, channel].to_numpy()[1:].astype(np.float64)

    def time(self):
        time_start = self.data.loc[:, "Start"].to_numpy()[0].astype(np.float64)
        time_increment = self.data.loc[:, "Increment"].to_numpy()[0].astype(np.float64)
        return np.arange(time_start, time_start + time_increment * len(self.get_channel_data("CH4")), time_increment)

    def plot_channels(self, channels = ["CH1", "CH2", "CH3", "CH4"]):
        fig, ax = plt.subplots()
        time = self.time()
        for channel in channels:
            ax.plot(time, self.get_channel_data(channel), label = channel)
        plt.xlabel("time (s)")
        plt.ylabel("amplitude (V)")
        plt.legend()
        plt.show()

    def fit_ringdown(self):
        data1 = self.get_channel_data("CH4")
        time1 = self.time()
        t0 = np.where(time1 > 0.)[0][0]
        time = time1[t0:]
        data = data1[t0:]
        fitter = Fitter(decay)
        fitter.set_absolute_sigma(False)
        fitter.set_data(time, data)
        fitter.set_p0({"tau": 8e-6})
        fitter.fit()
        fig, ax = plt.subplots()
        ax.plot(time, data)
        ax.plot(time, fitter.fitted_value(time))
        ax.set_xlabel("Time (s)")
        ax.set_ylabel("Transmission (V)")

        ax.text(0.02, 0.3, r"fit $y = Ae^{-t/\tau} + c$", transform=ax.transAxes)
        results_str = fitter.all_results_str()
        results_str = results_str[:results_str.find("tau")] + "$\\tau$" + results_str[results_str.find("tau") + 3:]
        ax.text(0.02, 0.1, results_str, transform=ax.transAxes)
        plt.grid()
        plt.show()
        return fitter.results["tau"], fitter.errors["Tau"]


oscilloscope = Oscilloscope("/home/icarus/Documents/data/manual/2024_03/11")
tau, err = oscilloscope.fit_ringdown()
print(tau, err)
