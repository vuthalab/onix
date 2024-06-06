from onix.analysis.microphone import Microphone
import matplotlib.pyplot as plt
import numpy as np
import time
import threading

def sine(x, A, omega, phi):
  return A * np.sin(omega*x + phi)

mic = Microphone(num_periods_fit = 1, num_periods_save = 1) # TODO: understand the sampling discontinuities

"""
last_time = time.time()
i = 0
while i < int(len(mic.buffer) / mic.samples_to_get):
  current_time = time.time()
  if current_time - last_time > mic.get_data_time:
    mic.get_data()
    last_time = time.time()
    i += 1
"""

#for i in range(int(len(mic.buffer) / mic.samples_to_get)):
#  mic.get_data()

get_data()

t = np.arange(0, len(mic.buffer) * mic.adc_interval, mic.adc_interval)
plt.scatter(t, mic.buffer, s = 1)

mic.get_fit()
plt.scatter(t, sine(t, mic.A, mic.omega, mic.phi), s = 1)

plt.show()

print(mic.phase, mic.period)

mic.close()
