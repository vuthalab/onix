import time
import os

import numpy as np

os.chdir("/home/onix/Documents/code")
os.environ["DATAFOLDER"] = "/home/onix/Documents/data"

from onix.data_tools import save_experiment_data

from onix.headers.digitizer import DigitizerVisa
from onix.headers.wavemeter.wavemeter import WM

wavemeter = WM()
dg = DigitizerVisa("192.168.0.125")
dg_channels = [1, 2]


import contextlib
import io
import sys

import pyttsx3
reader = pyttsx3.init()


## calibration at zero optical power
dg.autozero(dg_channels)

## set digitizer parameters
duration = 0.5
sample_rate = 1e3
voltage_range = 4

dg.configure_acquisition(
    sample_rate=sample_rate,
    samples_per_record=int(duration*sample_rate),
)
dg.configure_channels(
    channels=dg_channels,
    voltage_range=voltage_range,
)
dg.set_trigger_source_immediate()
dg.set_arm(triggers_per_arm=1)

def wavemeter_frequency():
    freq = wavemeter.read_frequency(5)
    if isinstance(freq, str):
        return -1
    return freq

## initialize data
frequency_before_GHz = []
V_transmission = []
V_monitor = []
frequency_after_GHz = []
times = []


## take data manually
dg.initiate_data_acquisition()
times.append(time.time())
frequency_before_GHz.append(wavemeter_frequency())
time.sleep(duration)
voltages = dg.get_waveforms(dg_channels)
V1 = voltages[0][0]
V2 = voltages[1][0]
V_transmission.append(V1)
V_monitor.append(V2)
frequency_after_GHz.append(wavemeter_frequency())
print(frequency_before_GHz[-1], np.average(V1), np.average(V2), np.average(V1 + V2), np.average(V1) / np.average(V2))


## take data loop
try:
    while True:
        dg.initiate_data_acquisition()
        freq_before = wavemeter_frequency()
        time.sleep(duration)
        voltages = dg.get_waveforms(dg_channels)
        V1 = voltages[0][0]
        V2 = voltages[1][0]
        # if np.average(V1) < 0.5 or np.average(V2) < 0.5:
        #     text = "Power too low."
        #     reader.say(text)
        #     reader.runAndWait()
        #     reader.stop()
        # elif np.average(V1) > 3.5 or np.average(V2) > 3.5:
        #     text = "Power too high."
        #     reader.say(text)
        #     reader.runAndWait()
        #     reader.stop()
        times.append(time.time())
        frequency_before_GHz.append(freq_before)
        V_transmission.append(V1)
        V_monitor.append(V2)
        frequency_after_GHz.append(wavemeter_frequency())
        print(f"{frequency_before_GHz[-1]:.3f}", f"{np.average(V1):.5f}", f"{np.average(V2):.5f}", f"{np.average(V1 + V2):.3f}", f"{np.average(V1) / np.average(V2):.4f}")
except KeyboardInterrupt:
    pass


## save data
data = {
    "times": times,
    "V_transmission": V_transmission,
    "V_monitor": V_monitor,
    "frequency_before_GHz": frequency_before_GHz,
    "frequency_after_GHz": frequency_after_GHz,
}
name = "Transmission"
data_id = save_experiment_data(name, data)
print(data_id)