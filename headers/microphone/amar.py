from onix.headers.microphone import Quarto
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import butter, sosfilt
from scipy.signal.windows import boxcar

q = Quarto()

data = []

for i in range(7): data.append(q.data())

data = np.array(data)
data = data.flatten()

N = 5000
stack = np.array([ np.roll(data,s) for s in range(N)])

stack_avg = np.average(stack,axis=0)

# data_averaged = [ np.mean(data[num-4:num+4]) for num, point in enumerate(data[4:-5], 4)]

xaxis = np.linspace(0, len(data)*10e-6, len(data))

# sos2 = butter(10, 50, 'lowpass', fs=100000, output='sos')

filtered2 = sosfilt(sos2, data)

# plt.plot(xaxis, data)
plt.plot(stack_avg - 0.3)
plt.show()

