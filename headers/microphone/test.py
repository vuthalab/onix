from onix.analysis.microphone import Microphone
import matplotlib.pyplot as plt
import numpy as np
import time

def sine(x,A,omega,phi):
    return A * np.sin(omega * x + phi)

mic = Microphone(num_periods_fit=3, num_periods_save=1, get_data_time=10e-3)

for i in range(int(np.ceil(2.4 / mic.get_data_time))):
    mic.get_data()
    time.sleep(mic.get_data_time)


plt.scatter(mic.t_axis, mic.buffer, s = 1)
plt.title("Raw data")
plt.show()


mic.get_fit()
print(mic.A, mic.omega, mic.phi)
plt.plot(mic.t_axis, sine(mic.t_axis, mic.A, mic.omega, mic.phi), alpha = 0.5)
plt.plot(mic.t_axis, mic.buffer, alpha = 0.5)
plt.show()
