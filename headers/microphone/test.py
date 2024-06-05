from onix.analysis.microphone import Microphone
import matplotlib.pyplot as plt
import numpy as np

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