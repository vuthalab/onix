from onix.headers.quarto_digitizer import Quarto
import time
import numpy as np
import matplotlib.pyplot as plt
from onix.analysis.power_spectrum import PowerSpectrum

q = Quarto()

adc_interval = 1e-6
segment_length = 32767
segment_number = 1
data_time = segment_length * segment_number * adc_interval

q.setup(segment_length, segment_number)
q.start()
time.sleep(data_time)
q.stop()
data = q.data()

index = np.arange(0,len(data))


fig, ax = plt.subplots()
ax.scatter(t_axis, data)
#ax.set_xlabel("Frequency (Hz)")
#ax.set_ylabel(r"Relative Voltage Noise V / $\sqrt{\mathrm{Hz}}$")
#ax.set_xscale("log")
#ax.set_yscale("log")
plt.show()