from onix.headers.microphone import Quarto
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import butter, sosfilt
from scipy.signal.windows import boxcar
import time
from scipy.signal import find_peaks
from scipy.optimize import curve_fit

def sin(t, f, A, phi, c):
    return A*np.sin(2*np.pi*f*t+phi)+c

q = Quarto()
adc_interval = q.adc_interval   # [s]
sample_rate = 1/adc_interval    # [samples per second]

data = np.array([])
fig, (ax1, ax2) = plt.subplots(2, 1)

for i in range(20): 
    data = np.append(data, q.data())

## windowed average
N = 5000
avgs = np.zeros_like(data)
for i in range(data.size):
    avgs[i] = np.mean(data[max(i-N, 0):i+1])

times = np.linspace(0, len(data)*10e-6, len(data))
avgs = avgs[times>0.5]
avgs -= np.mean(avgs)
times = times[times>0.5]

max_noise_freq = 5  # [Hz]
peak_distance = int(sample_rate/max_noise_freq)    # checking for peaks with frequency <= 5 Hz
peaks, properties = find_peaks(avgs, height=np.max(avgs)-0.001, distance=peak_distance)
average_time_dif_bw_peaks =  np.mean(np.abs(times[peaks] - np.roll(times[peaks], 1))[1:])
freq_estimate_from_peaks = 1/average_time_dif_bw_peaks

ax1.plot(times, avgs, label='avg', color='black')
ax1.set_xlabel('time (us)')
ax1.set_ylabel('signal with mean set to 0 (V)')
ax1.scatter(times[peaks], avgs[peaks], color='red')
ax1.set_title('averaged signal')

## FFT

avgs_fft = np.fft.rfft(avgs)
fft_freqs = np.fft.rfftfreq(avgs.size, 10e-6)

freq_peak = fft_freqs[np.argmax(avgs_fft)]

ax2.plot(fft_freqs, np.abs(avgs_fft), label='fft')
ax2.set_title('Fourier Transform of averaged signal')
ax2.set_xlabel('frequency (Hz)')
ax2.set_ylabel('signal with time domain \n mean set to 0 (V)')

## curvefit
print(f'FFT peak frequency = {freq_peak} Hz')
print(f'Frequency estimate from peaks = {freq_estimate_from_peaks} Hz')
p0=(freq_estimate_from_peaks, np.max(avgs), np.pi/2 - 2*np.pi*freq_estimate_from_peaks*times[peaks[0]], np.mean(avgs))

phi_pred = np.pi/2 - 2*np.pi*freq_estimate_from_peaks*times[peaks[0]]

popt, pcov = curve_fit(sin, times, avgs, p0=p0)
print(f"(f, A, phi, c)= {popt}")
ax1.plot(times, sin(times, *p0), label='curvefit')

plt.show()