import os
import numpy as np
import scipy.stats as st
import matplotlib.pyplot as plt

os.chdir("/home/onix/gdrive/code/onix_control/new")
os.environ["DATAFOLDER"] = "/home/onix/Desktop/data"

from data_tools import get_experiment_data, open_analysis_folder, get_analysis_file_path

_name = "Transmission"


## analysis
_data_number = 49
_data_name = f"#{_data_number}"
_data, _headers = get_experiment_data(_data_number)
_freqs = []
for kk in _data["frequency_after_GHz"]:
    try:
        _freqs.append(float(kk))
    except ValueError:
        _freqs.append(0)
_data["frequency_after_GHz"] = np.array(_freqs)
_V_transmission_avg = np.average(_data["V_transmission"], axis=1)
_V_transmission_err = np.std(_data["V_transmission"], axis=1) / np.sqrt(len(_data["V_transmission"]))
_V_monitor_avg = np.average(_data["V_monitor"], axis=1)
_V_monitor_err = np.std(_data["V_monitor"], axis=1) / np.sqrt(len(_data["V_monitor"]))
_V_transmission_ratio = _V_transmission_avg / _V_monitor_avg
_V_transmission_ratio_err = np.sqrt((_V_transmission_err / _V_monitor_avg) ** 2 + (_V_transmission_avg * _V_monitor_err / _V_monitor_avg**2) ** 2)


## save analysis
analysis_number = open_analysis_folder(_name)
print(analysis_number)
file_voltage_ratio = get_analysis_file_path(analysis_number, str(analysis_number) + "_normalized_transmission.pdf")
file_voltage_ratio_filter = get_analysis_file_path(analysis_number, str(analysis_number) + "_normalized_transmission_filtered.pdf")
analysis_name = f"#{analysis_number}"

## frequency mask
mask = np.bitwise_and(_data["frequency_after_GHz"] > 0, _V_monitor_avg > 0.1)

## binning
bin_size = 5 #GHz
frequencies = _data["frequency_after_GHz"][mask]
num_bins = int((np.max(frequencies) - np.min(frequencies)) / bin_size)
print(num_bins)

binned_means, bin_edges, binnumber = st.binned_statistic(frequencies, _V_transmission_ratio[mask], statistic="mean", bins = num_bins)
binned_stds, bin_edges, binnumber = st.binned_statistic(frequencies, _V_transmission_ratio[mask], statistic="std", bins = num_bins)
# binned_means_gaus, bin_edges_gaus, binnumber_gaus = st.binned_statistic(frequencies, all_data.normalized_gaussian_fit_amplitude, statistic = 'mean', bins=num_bins)

bin_width = bin_edges[1]-bin_edges[0]
print(bin_width)

x_ax = bin_edges[:-1] + bin_width / 2

## plot ratio
fig, ax = plt.subplots()
ax.errorbar(x_ax, binned_means, binned_stds, ls="none", marker="o")
#ax.errorbar(_data["frequency_after_GHz"][mask], _V_transmission_ratio[mask], _V_transmission_ratio_err[mask], ls="none", marker="o")

ax.text(0.02, 1.02, f"data {_data_name} analysis {analysis_name}", transform=ax.transAxes)
ax.set_xlabel("Wavemeter frequency (GHz)")
ax.set_ylabel("Transmission PD voltage / monitor PD voltage (V/V)")
plt.tight_layout()
plt.savefig(file_voltage_ratio)
plt.show()

## plot times
fig, ax = plt.subplots()
ax.errorbar(_data["times"][mask], _V_transmission_ratio[mask], _V_transmission_ratio_err[mask], ls="none", marker="o")
ax1 = ax.twinx()
ax1.scatter(_data["times"][mask], _data["frequency_after_GHz"][mask], color="C1")

# ax.scatter(_data["frequency_after_GHz"][mask], _V_transmission_avg[mask] + _V_monitor_avg[mask], marker="o")

ax.set_xlabel("Epoch time (s)")
ax.set_ylabel("Transmission PD voltage / monitor PD voltage (V/V)")
plt.tight_layout()
plt.show()

## plot transmission
plt.scatter(_data["frequency_after_GHz"], _V_transmission_avg)
plt.scatter(_data["frequency_after_GHz"], _V_monitor_avg)

plt.show()

## remove jumping data points
_freqs_selected = _freqs.copy()
_V_ratio_selected = _V_transmission_ratio.copy()

_jump_mask = np.zeros(len(_freqs), dtype=bool)
for kk in range(len(_freqs) - 2):
    freq_before = _freqs[kk]
    freq_now = _freqs[kk + 1]
    freq_after = _freqs[kk + 2]
    if np.abs(freq_now - freq_before) < 0.1 and np.abs(freq_after - freq_now) < 0.1:
        _jump_mask[kk + 1] = True


## plot ratio
fig, ax = plt.subplots()
#ax.errorbar(x_ax, binned_means, binned_stds, ls="none", marker="o")
ax.errorbar(_data["frequency_after_GHz"][_jump_mask], _V_transmission_ratio[_jump_mask], _V_transmission_ratio_err[_jump_mask], ls="none", marker="o")

ax.text(0.02, 1.02, f"data {_data_name} analysis {analysis_name}", transform=ax.transAxes)
ax.set_xlabel("Wavemeter frequency (GHz)")
ax.set_ylabel("Transmission PD voltage / monitor PD voltage (V/V)")
plt.tight_layout()
plt.savefig(file_voltage_ratio_filter)
plt.show()


