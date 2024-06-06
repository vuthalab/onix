from onix.analysis.microphone import Microphone
import matplotlib.pyplot as plt
import numpy as np

"""
def sine(x,A,omega,phi):
    return A * np.sin(omega * x + phi)

mic = Microphone()
for i in range(8000):
    mic.get_data()

plt.scatter(mic.t_axis, mic.buffer, s = 1)
plt.title("Raw data")
plt.show()

mic.get_fit()
print(mic.A, mic.omega, mic.phi)
plt.plot(mic.t_axis, sine(mic.t_axis, mic.A, mic.omega, mic.phi), alpha = 0.5)
plt.plot(mic.t_axis, mic.buffer, alpha = 0.5)
plt.show()
"""

# 0.03 s = max samples each time, so get data 80 times


"""
mic = Microphone(num_periods_fit=3)
for i in range(80):
    mic.get_data()

plt.plot(mic.buffer)
plt.show()
"""

from onix.headers.microphone import Quarto
q = Quarto()
import time
print(q.adc_interval)
data = []
for i in range(80):
    data.append(q.data())
    time.sleep(0.03)
data = np.array(data)
data = data.flatten()
t_axis = np.linspace(0, len(data)*q.adc_interval, len(data))
#print(len(data), len(t_axis))
plt.scatter(t_axis, data, s = 1)
plt.show()