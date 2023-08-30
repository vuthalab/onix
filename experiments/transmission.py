import time
import os

import numpy as np

os.chdir("/home/onix/Documents/code")
os.environ["DATAFOLDER"] = "/home/onix/Documents/data"

from onix.data_tools import save_experiment_data

from onix.headers.digitizer import Digitizer
from onix.headers.wavemeter.wavemeter import WM

wavemeter = WM()
dg = Digitizer("192.168.0.125")


import contextlib
import io
import sys

@contextlib.contextmanager
def nostdout():
    save_stdout = sys.stdout
    sys.stdout = io.StringIO()
    yield
    sys.stdout = save_stdout


## set digitizer parameters
params_dict = {
    "num_samples": 1e3, #will be coerced up to multiple of 4
    "sampling_rate": 1e3,
    "ch1_voltage_range": 2,
    "ch2_voltage_range": 2,
    "trigger_channel": 3, # 1 -> ch1, 2 -> ch2, 0 -> ext, else -> immediate
    "data_format": "float32",# "float32" or "adc16"
    "coupling": "DC",
    "num_records": 1,
    "triggers_per_arm": 1,
}
dg.set_parameters(params_dict)
dg.configure()

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
with nostdout():
    dg.crude_trigger()
times.append(time.time())
frequency_before_GHz.append(wavemeter_frequency())
time.sleep(1)
V1, V2 = dg.get_two_channel_waveform()
V_transmission.append(V1)
V_monitor.append(V2)
frequency_after_GHz.append(wavemeter_frequency())
print(frequency_before_GHz[-1], np.average(V1), np.average(V2), np.average(V1 + V2), np.average(V1 / V2))


## take data loop
try:
    while True:
        with nostdout():
            dg.crude_trigger()
        freq_before = wavemeter_frequency()
        time.sleep(1)
        V1, V2 = dg.get_two_channel_waveform()
        frequency_before_GHz.append(freq_before)
        times.append(time.time())
        V_transmission.append(V1)
        V_monitor.append(V2)
        frequency_after_GHz.append(wavemeter_frequency())
        print(f"{frequency_before_GHz[-1]:.3f}", f"{np.average(V1):.3f}", f"{np.average(V2):.3f}", f"{np.average(V1 + V2):.3f}", f"{np.average(V1 / V2):.3f}")
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