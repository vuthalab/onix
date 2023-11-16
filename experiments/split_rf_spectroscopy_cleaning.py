import time

import numpy as np
from onix.data_tools import save_experiment_data
from onix.units import ureg

from onix.headers.pcie_digitizer.pcie_digitizer import Digitizer
from onix.headers.wavemeter.wavemeter import WM
from onix.headers.awg.M4i6622 import M4i6622
from onix.sequences.split_rf_spectroscopy import SplitRFSpectroscopy
import matplotlib.pyplot as plt
import sys

wavemeter = WM()

def wavemeter_frequency():
    freq = wavemeter.read_frequency(params["wm_channel"])
    if isinstance(freq, str):
        return -1
    return freq

m4i = M4i6622()

#offset = float(sys.argv[1])
#print(offset)

## parameters

params = {
    "wm_channel": 5,

    "digitizer_channel": 0,
    "field_plate_channel": 1,
    "rf_channel": 2,

    "repeats": 5,

    "ao": {
        "channel": 0,
        "frequency": 80 * ureg.MHz,
        "amplitude": 1800,
        "detect_amplitude": 600,
    },

    "eo": {
        "channel": 1,
        "offset": -300 * ureg.MHz,
        "amplitude": 24000,
    },

    "detect_ao": {
        "channel": 3,
        "frequency": 80 * ureg.MHz,
        "amplitude": 0,
    },

    "burn": {
        "transition": "bb",
        "duration": 7 * ureg.s,
        "scan": 5 * ureg.MHz,
        "detuning": 0 * ureg.MHz,
    },

    "repop": {
        "transitions": ["ca", "ac"],
        "duration": 0.6 * ureg.s,
        "scan": 0.3 * ureg.MHz,
        "detuning": 0 * ureg.MHz,
    },

    "flop": {
        "transition": "ab",
        "step_frequency": 5 * ureg.kHz,
        "step_time": 0.5 * ureg.ms,
        "on_time": 0.5 * ureg.ms,
        "amplitude": 6000,  # do not go above 6000.
        "offset": 0 * ureg.kHz,
        "scan": 1 * ureg.kHz,
        "repeats": 1,
    },

    "detect": {
        "transition": "bb",
        "detunings": np.linspace(-2.5, 2.5, 51) * ureg.MHz,
        "on_time": 16 * ureg.us,
        "off_time": 8 * ureg.us,
        "delay_time": 300 * ureg.ms,
        "repeats": 200,
        "ttl_detect_offset_time": 4 * ureg.us,
        "ttl_start_time": 12 * ureg.us,
        "ttl_duration": 4 * ureg.us,
    },
}

## setup sequence
sequence = SplitRFSpectroscopy(
    ao_parameters=params["ao"],
    eo_parameters=params["eo"],
    detect_ao_parameters=params["detect_ao"],
    burn_parameters=params["burn"],
    repop_parameters=params["repop"],
    flop_parameters=params["flop"],
    detect_parameters=params["detect"],
    digitizer_channel=params["digitizer_channel"],
    field_plate_channel=params["field_plate_channel"],
    rf_channel=params["rf_channel"],
)
sequence.setup_sequence()

## setup the awg and digitizer
m4i.setup_sequence(sequence)


##

def data_cleaning(data, sample_rate):
    delay_time = params["detect"]["ttl_detect_offset_time"].to('s').magnitude
    on_time = params["detect"]["on_time"].to('s').magnitude
    off_time = params["detect"]["off_time"].to('s').magnitude
    steps = len(params["detect"]["detunings"])

    rise_delay = 3e-6
    fall_delay = 1e-6

    data_width = int((on_time - rise_delay - fall_delay)*sample_rate)

    start_index = int((delay_time + rise_delay) * sample_rate)
    stop_index = start_index + data_width

    mask = np.ones_like(data[0])

    for i in range(steps):
        first_index = start_index + i * (int((fall_delay + off_time + rise_delay) * sample_rate) + data_width)
        last_index = first_index + data_width

        mask[first_index : last_index] = 0

    means = []
    errs = []
    for run in data:
        masked = np.ma.masked_array(run, mask).compressed()
        split = np.split(masked, steps)

        mean = np.mean(split, axis=1)
        err = np.std(split, axis=1) / np.sqrt(len(split[0]))

        means.append(mean)
        errs.append(err)

    sorted = np.reshape(means, (4 * params["repeats"], params["detect"]["repeats"], steps))
    sortederrs = np.reshape(errs, (4 * params["repeats"], params["detect"]["repeats"], steps))

    return sorted, sortederrs



## take data
sample_rate = int(1e8)
dg = Digitizer(False)
val = dg.configure_system(
    mode=2,
    sample_rate=sample_rate,
    segment_size=int(sequence.detect_time.to("s").magnitude * sample_rate),
    segment_count= int(sequence.num_of_records() * params['repeats']),
    voltage_range = 2000
)

val = dg.configure_trigger(
    edge = 'rising',
    level = 30,
    source = -1,
    coupling = 1,
    range = 10000
)


acq_params = dg.get_acquisition_parameters()

epoch_times = []
transmissions = None
reflections = None
for kk in range(0):
    m4i.start_sequence()
    m4i.wait_for_sequence_complete()
dg.arm_digitizer()
time.sleep(0.1)

for kk in range(params["repeats"]):
    print(f"{kk / params['repeats'] * 100:.0f}%")
    m4i.start_sequence()
    epoch_times.append(time.time())
    m4i.wait_for_sequence_complete()
m4i.stop_sequence()

digitizer_data = dg.get_data()

##

transmissions = np.array(digitizer_data[0])
reflections = np.array(digitizer_data[1])

transmission_means, transmission_errs = data_cleaning(transmissions, sample_rate)

reflection_means, reflection_errs = data_cleaning(reflections, sample_rate)

## plot
#plt.plot(digitizer_data[0][100])
plt.errorbar(params["detect"]["detunings"], means[3][0]/reflection_means[3][0], errs[3][0], fmt='.')

plt.show()

## save data
data = {
    "times": photodiode_times,
    "transmissions": transmissions,
    "monitors": reflections,
    "epoch_times": epoch_times,
}
headers = {
    "params": params,
    "wavemeter_frequency": wavemeter_frequency(),
}
name = "Split RF Spectroscopy"
data_id = save_experiment_data(name, data, headers)
print(data_id)

## empty