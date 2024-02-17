import time
import os
import numpy as np

# os.chdir("/home/onix/Documents/code")
# os.environ["DATAFOLDER"] = "/home/onix/Documents/data"

#os.environ["DATAFOLDER"] = "/home/icarus/Documents/data"

from onix.data_tools import save_experiment_data

from onix.headers.RigolDS1102 import RigolDS1102
from onix.headers.wavemeter.wavemeter import WM

wavemeter = WM()
# dg = DigitizerVisa("192.168.0.125")
# dg_channels = [1, 2]


import contextlib
import io
import sys
#
# import pyttsx3
# reader = pyttsx3.init()


## calibration at zero optical power
# dg.autozero(dg_channels)

## set scope parameters

scope = RigolDS1102(path='/dev/usbtmc2')
scope.write(":key:force")
scope.write(":key:lock disable")

def wavemeter_frequency():
    freq = wavemeter.read_frequency(5)
    if isinstance(freq, str):
        return -1
    return freq

def get_contrast():
    fringes = wavemeter._format_str_array(wavemeter._fetch_interferogram(channel=5))
    fringes_mid = fringes[410:615]
    fmax = np.max(fringes)
    fmin = np.min(fringes)

    fmax_mid = np.max(fringes_mid)
    fmin_mid = np.min(fringes_mid)
    contrast = (fmax_mid - fmin_mid) / (fmax + fmin)
    # print(f'Measured contrast is {contrast}')
    return contrast

def get_data():
    curr_scope = scope.ReadScope()
    ch1_out = curr_scope[1]
    ch2_out = curr_scope[2]
    #signal = np.mean(ch1_out)
    #signal_err = np.std(ch1_out)/np.sqrt(len(ch1_out))
    #normalizer = np.mean(ch2_out)
    #normalizer_err = np.std(ch2_out)/np.sqrt(len(ch2_out))

    return [ch1_out, ch2_out]

## initialize data
frequency_before_GHz = []
V_transmission = []
V_monitor = []
frequency_after_GHz = []
contrast_after = []
times = []



## take data manually

data = get_data()

V1 = data[0]
V2 = data[1]
times.append(time.time())

frequency_before_GHz.append(wavemeter_frequency())

V_transmission.append(V1)
V_monitor.append(V2)

frequency_after_GHz.append(wavemeter_frequency())
contrast_after.append(get_contrast())
print(frequency_before_GHz[-1], contrast_after[-1], np.average(V1), np.average(V2), np.average(V1 + V2), np.average(V1) / np.average(V2))
print("transmission", np.average(V1), "normalizer", np.average(V2), "contrast", contrast_after[-1])



 ## take data loop
try:
    while True:
        data = get_data()

        V1 = data[0]
        V2 = data[1]
        times.append(time.time())

        frequency_before_GHz.append(wavemeter_frequency())

        V_transmission.append(V1)
        V_monitor.append(V2)

        frequency_after_GHz.append(wavemeter_frequency())
        contrast_after.append(get_contrast())
        print(frequency_before_GHz[-1], contrast_after[-1], np.average(V1), np.average(V2), np.average(V1 + V2), np.average(V1) / np.average(V2))
        print("transmission", np.average(V1), "normalizer", np.average(V2), "contrast", contrast_after[-1])
        time.sleep(30)

except KeyboardInterrupt:
    pass


## save data
data = {
    "times": times,

    "V_transmission": V_transmission,
    "V_monitor": V_monitor,
    "frequency_before_GHz": frequency_before_GHz,
    "frequency_after_GHz": frequency_after_GHz,
    "contrast_after": contrast_after,
}
name = "Transmission"
data_id = save_experiment_data(name, data)
print(data_id)