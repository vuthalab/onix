from onix.headers.microphone import Quarto
from onix.analysis.fitter import Fitter
from onix.data_tools import save_experiment_data

import numpy as np
import matplotlib.pyplot as plt
import time

from pprint import pprint

from scipy.signal import find_peaks
from scipy.optimize import curve_fit

def sin(t, f, A, phi, c):
    return A*np.sin(2*np.pi*f*t+phi)+c

q = Quarto()
adc_interval = q.adc_interval   # [s]
sample_rate = 1/adc_interval    # [samples per second]
data_length = 30000
data_time = 5*60                # [s]
repeats = int(data_time*sample_rate/data_length)+1

headers = {'adc_interval': adc_interval, 
           'sample_rate': sample_rate, 
           'data_length': data_length,
           'data_time': data_time,
           'repeats': repeats}


data = np.array([])
data_dict = {}

start = time.perf_counter()
for i in range(repeats): 
    data_dict[f'{i}'] = q.data()
    data = np.append(data, data_dict[f'{i}'])
    time.sleep(adc_interval*data_length)
end = time.perf_counter()

print(f'Time taken to get data: {end-start} sec. Expected time = {(repeats*data_length)/sample_rate} sec.')

name = 'PulseTubeNoise'
data_id = save_experiment_data(data_name=name, data=data_dict, headers=headers)
print(data_id)


# fft_dict = {i: (np.fft.rfftfreq(sample.size, 10e-6), np.fft.rfft(sample)) for i, sample in data_dict.items()}

"""
plt.plot(data)
plt.show()
print(data.size)
"""

## windowed average
"""
N = 5000
avgs = np.zeros_like(data)
for i in range(data.size):
    avgs[i] = np.mean(data[max(i-N, 0):i+1])

times = np.linspace(0, len(data)*10e-6, len(data))
avgs = avgs[times>0.5]
avgs -= np.mean(avgs)
times = times[times>0.5]    # cutting out transients
"""

"""
max_noise_freq = 5  # [Hz]
peak_distance = int(sample_rate/max_noise_freq)    # checking for peaks with frequency <= 5 Hz
peaks, properties = find_peaks(avgs, height=np.max(avgs)-0.001, distance=peak_distance)
time_dif_bw_peaks =  np.abs(times[peaks] - np.roll(times[peaks], 1))[1:]
freq_estimate_from_peaks = 1/np.mean(time_dif_bw_peaks)

print(f'Frequency estimate from peaks = {freq_estimate_from_peaks} Hz from {time_dif_bw_peaks.size} samples')
fig, (ax1, ax2) = plt.subplots(2, 1)
ax1.plot(times, avgs, label='avg', color='black')
ax1.set_xlabel('time (s)')
ax1.set_ylabel('signal with mean set to 0 (V)')
ax1.scatter(times[peaks], avgs[peaks], color='red')
ax1.set_title('averaged signal')
"""

## FFT
"""
fig, (ax1, ax2) = plt.subplots(2, 1)
avgs_fft = np.fft.rfft(avgs)
fft_freqs = np.fft.rfftfreq(avgs.size, 10e-6)

freq_peak = fft_freqs[np.argmax(avgs_fft)]
print(f'FFT peak frequency = {freq_peak} Hz')

ax2.plot(fft_freqs, np.abs(avgs_fft), label='fft')
ax2.set_title('Fourier Transform of averaged signal')
ax2.set_xlabel('frequency (Hz)')
ax2.set_ylabel('signal with time domain \n mean set to 0 (V)')

plt.show()
"""

## curvefit
"""
phi_pred0 = np.pi/2 - 2*np.pi*freq_estimate_from_peaks*times[peaks[0]]
phi_pred_acc = np.angle(np.exp(1j*phi_pred0))
p0= {'f': freq_estimate_from_peaks, 'A': np.max(avgs), 'phi':  phi_pred_acc, 'c': np.mean(avgs)}
bounds = {'f': (0, 5), 'A': (0, np.max(avgs)), 'phi': (-np.pi, np.pi), 'c': (-np.fabs(np.mean(avgs)), np.fabs(np.mean(avgs)))}

# between 3.34 and 3.35 Hz seems like the usual frequency

if time_dif_bw_peaks.size >= 5: #TODO: remove magic number
    fitter = Fitter(sin)
    fitter.set_data(times, avgs)
    fitter.set_p0(p0)

    for param in bounds.keys():
        fitter.set_bounds(param, *bounds[param])

    fitter.fit()
    popt = fitter.results

    # popt, pcov = curve_fit(sin, times, avgs, p0=tuple(p0.values()))
    print(f"(f, A, phi, c)= {popt}")
    fig, ax1 = plt.subplots(1, 1)
    ax1.plot(times, sin(times, **p0), label='curvefit')
    ax1.plot(times, avgs, label='avg', color='black')
    ax1.set_xlabel('time (s)')
    ax1.set_ylabel('signal with mean set to 0 (V)')
    ax1.scatter(times[peaks], avgs[peaks], color='red')
    ax1.set_title('averaged signal')

    ax1.legend()

    plt.show()
"""