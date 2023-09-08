import time
import os

import numpy as np

os.chdir("/home/onix/Documents/code")
os.environ["DATAFOLDER"] = "/home/onix/Documents/data"

from onix.data_tools import save_experiment_data
from onix.units import ureg

from onix.headers.wavemeter.wavemeter import WM
from onix.sequences.antihole_eo import AntiholeEO
import matplotlib.pyplot as plt

wavemeter = WM()

params = {
    "wm_channel": 5,

    "eo_channel": 1,
    "eo_max_amplitude": 2400,
    "eo_offset_frequency": -300 * ureg.MHz,

    "switch_aom_channel": 0,
    "switch_aom_frequency": 80 * ureg.MHz,
    "switch_aom_amplitude": 2400,
    "switch_aom_probe_amplitude": 150,

    "burn_width": 1 * ureg.MHz,
    "burn_time": 1 * ureg.s,

    "pump_time": 0.1 * ureg.s,

    "probe_detunings": np.linspace(-1.5, 1.5, 20) * ureg.MHz,
    "probe_on_time": 12 * ureg.us,
    "probe_off_time": 8 * ureg.us,
    "probe_repeats": 1,
    "ttl_probe_offset_time": 4 * ureg.us,

    "repeats": 1,
}

def wavemeter_frequency():
    freq = wavemeter.read_frequency(params["wm_channel"])
    if isinstance(freq, str):
        return -1
    return freq

## setup sequence
sequence = AntiholeEO(
    probe_transition="bb",
    eo_channel=params["eo_channel"],
    eo_offset_frequency=params["eo_offset_frequency"],
    switch_aom_channel=params["switch_aom_channel"],
    switch_aom_frequency=params["switch_aom_frequency"],
    switch_aom_amplitude=params["switch_aom_amplitude"],
    repeats=params["repeats"],
)
sequence.add_burns(
    burn_width=params["burn_width"],
    burn_time=params["burn_time"],
    burn_amplitude=params["eo_max_amplitude"],
)
sequence.add_pumps(
    pump_time=params["pump_time"],
    pump_amplitude=params["eo_max_amplitude"],
)
sequence.add_probe(
    probe_detunings=params["probe_detunings"],
    probe_amplitude=params["eo_max_amplitude"],
    aom_probe_amplitude=params["switch_aom_probe_amplitude"],
    on_time=params["probe_on_time"],
    off_time=params["probe_off_time"],
)
sequence.add_break()
sequence.setup_sequence(probe_repeats=params["probe_repeats"])

## setup the awg
sequence.setup_m4i()

## setup the digitizer
sequence.setup_digitizer("192.168.0.125")
time.sleep(sequence.total_duration)

## take data
epoch_times = []
photodiode_voltages = []

for kk in range(params["repeats"]):
    sequence.m4i.startCard(False)
    epoch_times.append(time.time())
    time.sleep(sequence.total_duration)

for kk in range((1 + params["repeats"]) * 3 * params["probe_repeats"]):
    V1, _ = sequence.dg.get_two_channel_waveform(kk + 1)
    if kk < 3 * params["probe_repeats"]:
        continue
    photodiode_voltages.append(V1)

photodiode_times = [kk / sequence.sampling_rate for kk in range(len(V1))]

## plot
plt.plot(photodiode_times, np.transpose(photodiode_voltages)); plt.legend(); plt.show();

## stops the awg
sequence.m4i.stop()

## save data
data = {
    "photodiode_times": photodiode_times,
    "photodiode_voltages": photodiode_voltages,
    "epoch_times": epoch_times,
}
headers = {
    "params": params,
    "wavemeter_frequency": wavemeter_frequency(),
}
name = "Antihole EO"
data_id = save_experiment_data(name, data)
print(data_id)
