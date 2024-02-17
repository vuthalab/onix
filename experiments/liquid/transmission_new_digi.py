import time
import os
import numpy as np

# os.chdir("/home/onix/Documents/code")
# os.environ["DATAFOLDER"] = "/home/onix/Documents/data"

#os.environ["DATAFOLDER"] = "/home/icarus/Documents/data"

from onix.data_tools import save_experiment_data

from onix.headers.pcie_digitizer.pcie_digitizer import Digitizer
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

## set digitizer parameters
try:
    dg
    print("dg is already defined.")
except Exception:
    dg = Digitizer()


set_sample_rate = 100e6
duration = 0.1
dg.set_acquisition_config(
    num_channels=2,
    sample_rate=set_sample_rate,
    segment_size=int(duration * set_sample_rate),
    segment_count=1,
)

dg.set_channel_config(channel=1, range=1, high_impedance=True)
dg.set_channel_config(channel=2, range=5, high_impedance=True)
dg.set_trigger_source_software()
dg.write_configs_to_device()

#
# dg.configure_acquisition(
#     sample_rate=sample_rate,
#     samples_per_record=int(duration*sample_rate),
# )
# dg.configure_channels(
#     channels=dg_channels,
#     voltage_range=voltage_range,
# )
# dg.set_trigger_source_immediate()
# dg.set_arm(triggers_per_arm=1)
#
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

## initialize data
frequency_before_GHz = []
V_transmission = []
V_monitor = []
frequency_after_GHz = []
contrast_after = []
times = []



## take data manually
dg.start_capture()
timeout = 1
dg.wait_for_data_ready(duration+timeout)
sample_rate, data = dg.get_data()

V1 = data[0][0]
V2 = data[1][0]

times.append(time.time())

frequency_before_GHz.append(wavemeter_frequency())

V_transmission.append(V1)
V_monitor.append(V2)

frequency_after_GHz.append(wavemeter_frequency())
contrast_after.append(get_contrast())
print(V2)
print(frequency_before_GHz[-1], contrast_after[-1], np.average(V1), np.average(V2), np.average(V1 + V2), np.average(V1) / np.average(V2))
print("transmission", np.average(V1), "normalizer", np.average(V2), "contrast", contrast_after[-1])



 ## take data loop
try:
    while True:
        """dg.initiate_data_acquisition()
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
        print(f"{frequency_before_GHz[-1]:.3f}", f"{np.average(V1):.5f}", f"{np.average(V2):.5f}", f"{np.average(V1 + V2):.3f}", f"{np.average(V1) / np.average(V2):.4f}")"""
        dg.start_capture()
        timeout = 1
        dg.wait_for_data_ready(duration+timeout)
        sample_rate, data = dg.get_data()

        V1 = data[0][0]
        V2 = data[1][0]
        times.append(time.time())

        frequency_before_GHz.append(wavemeter_frequency())

        V_transmission.append(V1)
        V_monitor.append(V2)

        frequency_after_GHz.append(wavemeter_frequency())
        contrast_after.append(get_contrast())
        print(V2)
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