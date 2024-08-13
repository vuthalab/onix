from onix.headers.quarto_digitizer import Quarto
import time
import numpy as np
import matplotlib.pyplot as plt
from onix.analysis.power_spectrum import PowerSpectrum
from onix.headers.awg.M4i6622 import M4i6622
q = Quarto()


try:
    m4i  # type: ignore
    print("m4i is already defined.")
except Exception:
    try:
        m4i = M4i6622()
    except Exception as e:
        m4i = None
        print("m4i is not defined with error:")
        print(traceback.format_exc())


adc_interval = 2e-6
segment_length = 32767
segment_number = 1
data_time = segment_length * segment_number * adc_interval

# noise = PowerSpectrum(segment_length * segment_number, adc_interval)
N = 1
actual_period = 1e-4

def ranges(nums):
    nums = sorted(set(nums))
    gaps = [[s, e] for s, e in zip(nums, nums[1:]) if s+1 < e]
    edges = iter(nums[:1] + sum(gaps, []) + nums[-1:])
    return list(zip(edges, edges))

def gaussian(ts, a, mu, sigma):
    return a * np.exp(-(ts-mu)**2 / (2 * sigma ** 2))

# fig, ax = plt.subplots()
# ax.plot(noise.f, noise.relative_voltage_spectrum)
# ax.set_xlabel("Frequency (Hz)")
# ax.set_ylabel(r"Relative Voltage Noise V / $\sqrt{\mathrm{Hz}}$")
# ax.set_xscale("log")
# ax.set_yscale("log")
# plt.show()

# time series data
q.setup(segment_length, segment_number)
q.start()
time.sleep(2*data_time)
print(2*data_time)
q.stop()
# noise.add_data(q.data())
t = np.arange(0, data_time, adc_interval)
data_all = q.data()
data = data_all[0][0]
data2 = data_all[1][0]


fig, axs = plt.subplots(1, 2)
ax1 = axs[0]
ax2 = axs[1]
ax1.plot(data)
print(len(data))
print(len(data2))
ax2.plot(data2)
ax1.set_xlabel("Time (s)")
ax1.set_ylabel("Voltage (V)")
plt.show()



## get data
# periods = np.array([])
# for i in range(N):
#     # time series data
#     q.setup(segment_length, segment_number)
#     q.start()
#     time.sleep(data_time)
#     q.stop()
#     # noise.add_data(q.data())
#     t = np.arange(0, data_time, adc_interval)
#     data_all = q.data()
#     data = data_all[0][0]
#
#     # interpolate
#     t_interp = np.arange(0, data_time, adc_interval/100)
#     data_interp = np.interp(t_interp, t, data)
#
#     # use interpolation to find cross 0
#     max_data = np.max(data)
#     halfway_mask = np.bitwise_and(data_interp < max_data/100, data_interp > -max_data/100)
#     t_halfway = t_interp[halfway_mask]
#     data_halfway = data_interp[halfway_mask]
#
#     t_idx = np.where(halfway_mask)[0]
#     t_idx_ranges = ranges(t_idx)
#
#     intersections = []
#     for t_idx_range in t_idx_ranges:
#         t1 = t_interp[t_idx_range[0]]
#         t2 = t_interp[t_idx_range[-1]]
#         y1 = data_interp[t_idx_range[0]]
#         y2 = data_interp[t_idx_range[-1]]
#         slope = (y2-y1)/(t2-t1)
#         intercept = y1 - slope*t1
#         intersection = -intercept/slope
#         if slope < 0:
#             intersections.append(intersection)
#
#     intersections = np.array(intersections)
#     periods_n = np.array([intersections[i+1] - intersections[i] for i in range(len(intersections)-1)])
#     periods = np.append(periods, periods_n)
#
# ##
#
# periods_avg = np.average(periods)
# periods_std = np.std(periods)
#
# print(periods_avg-actual_period)
# print(periods_std)
#
# ## plot
# fig, axs = plt.subplots(1, 2)
# ax1 = axs[0]
# ax2 = axs[1]
#
# ax1.plot(t, data, label="raw")
# # ax1.plot(t_interp, data_interp, '.')
# ax1.plot(t_halfway, data_halfway, '.', label="interp near 0")
# ax1.plot(intersections, np.zeros(len(intersections)), '.', label="interp cross 0 and falling edge")
# ax1.set_xlabel("Time (s)")
# ax1.set_ylabel("Voltage (V)")
# ax1.legend()
#
# # ax2.hist(periods-actual_period, bins=20)
# counts, bins = np.histogram(periods-actual_period, bins=30)
# ax2.stairs(counts, bins, fill=True)
# gauss_ts = np.linspace(np.min(periods)-actual_period, np.max(periods)-actual_period, 100)
# ax2.plot(gauss_ts, gaussian(gauss_ts, np.max(counts), periods_avg-actual_period, periods_std))
# ax2.set_xlabel("Jitter (s)")
# ax2.set_ylabel("Occurances")
# ax2.ticklabel_format(useOffset=False)
# plt.tight_layout()
# plt.show()
