import numpy as np
import matplotlib.pyplot as plt
import os
import pandas as pd
from onix.analysis.fitter import Fitter

os.chdir("/home/icarus/Documents/data/manual/2024_02/19/")
data = pd.read_csv("cavity_oscilloscope_data.csv")
params = pd.read_csv("cavity_oscilloscope_params.txt")


reflection = data.loc[:, "CH2"].to_numpy()[1:].astype(np.float128)
error = data.loc[:, "CH3"].to_numpy()[1:].astype(np.float128)
transmission = data.loc[:, "CH4"].to_numpy()[1:].astype(np.float128)

time_start = data.loc[:, "Start"].to_numpy()[0].astype(np.float128)
time_increment = data.loc[:, "Increment"].to_numpy()[0].astype(np.float128)
time = np.arange(time_start, time_start + time_increment*len(reflection), time_increment)

fig, ax = plt.subplots()
# ax.plot(reflection, label="reflection")
ax.plot(time, error, label="error")
ax.plot(time, transmission, label="transmission")
plt.xlabel("time (s)")
plt.ylabel("detector amplitude (V)")
plt.legend()
plt.show()