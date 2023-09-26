import time
import os

import numpy as np
from onix.data_tools import save_experiment_data
from onix.units import ureg

from onix.headers.digitizer import DigitizerVisa
from onix.headers.wavemeter.wavemeter import WM
from onix.headers.awg.M4i6622 import M4i6622
from onix.sequences.antihole_eo import AntiholeEO
import matplotlib.pyplot as plt

wavemeter = WM()

def wavemeter_frequency():
    freq = wavemeter.read_frequency(params["wm_channel"])
    if isinstance(freq, str):
        return -1
    return freq

m4i = M4i6622()
dg = DigitizerVisa("192.168.0.125")

## parameters

params = {
    "wm_channel": 5,

    "eo_channel": 1,
    "eo_max_amplitude": 3200,
    "eo_offset_frequency": -99 * ureg.MHz,

    "switch_aom_channel": 0,
    "switch_aom_frequency": 80 * ureg.MHz,
    "switch_aom_amplitude": 2400,
    "switch_aom_probe_amplitude": 40,

    "burn_width": 2 * ureg.MHz,
    "burn_time": 5 * ureg.s,

    "pump_time": 0.0 * ureg.s,

    "probe_detunings": np.linspace(-0.5, 0.5, 20) * ureg.MHz,
    "probe_on_time": 16 * ureg.us,
    "probe_off_time": 8 * ureg.us,
    "probe_repeats": 20,
    "ttl_probe_offset_time": 4 * ureg.us,

    "repeats": 1,
}

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

## setup the awg and digitizer
m4i.setup_sequence(sequence)

sample_rate = 1e7
dg.configure_acquisition(
    sample_rate=sample_rate,
    samples_per_record=int(sequence.probe_read_time.to("s").magnitude * sample_rate),
    num_records=sequence.num_of_records(params["repeats"]),
)
dg.configure_channels(channels=[1], voltage_range=1)
dg.set_trigger_source_external()
dg.set_arm(triggers_per_arm=sequence.num_of_records(params["repeats"]))

## take data
epoch_times = []
photodiode_voltages = []

dg.initiate_data_acquisition()
m4i.start_sequence()
m4i.wait_for_sequence_complete()
time.sleep(0.1)
for kk in range(params["repeats"]):
    m4i.start_sequence()
    epoch_times.append(time.time())
    m4i.wait_for_sequence_complete()
    time.sleep(0.1)
m4i.stop_sequence()

photodiode_voltages = dg.get_waveforms([1], records=(1, sequence.num_of_records(params["repeats"])))[0]
photodiode_times = [kk / sample_rate for kk in range(len(photodiode_voltages[0]))]

## plot
#plt.plot(photodiode_times, np.transpose(photodiode_voltages)); plt.legend(); plt.show();

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
data_id = save_experiment_data(name, data, headers)
print(data_id)

## empty