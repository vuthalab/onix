# %%
from onix.data_tools import get_experiment_data
import numpy as np
import matplotlib.pyplot as plt

# %%
data_dict, headers = get_experiment_data(529025) # 525307, 525310
adc_interval = headers['adc_interval']
data_length = headers['data_length']
repeats = headers['repeats']
N = 5000
transient_time = 0.01 # [s]


# %%
data = np.array([])
for i, data_array in data_dict.items():
    data = np.append(data, data_array)

times = np.linspace(0, 50*data_length*adc_interval, 50*data_length)

avgs = np.zeros_like(data)
for i in range(data.size):
    avgs[i] = np.mean(data[max(i-N, 0):i+1])

plt.plot(times[0:int(10e5)], avgs[0:int(10e5)])
plt.show()

# %%



