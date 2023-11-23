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

#flop_time = float(sys.argv[1])
#print(flop_time)

#offset = float(sys.argv[1])
#print(offset)

## parameters

params = {
    "wm_channel": 5,

    "digitizer_channel": 0,
    "field_plate_channel": 1,
    "rf_channel": 2,

    "repeats": 3,

    "ao": {
        "channel": 0,
        "frequency": 80 * ureg.MHz,
        "amplitude": 2400,
        "detect_amplitude": 400,
    },

    "eo": {
        "channel": 1,
        "offset": -300 * ureg.MHz,
        "amplitude": 0,
    },

    "detect_ao": {
        "channel": 3,
        "frequency": 80 * ureg.MHz,
        "amplitude": 0,
    },

    "burn": {
        "transition": "bb",
        "duration": 1 * ureg.s,
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
        "step_time": 1 * ureg.ms,
        "on_time": 50 * ureg.us,
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
        "delay_time": 30 * ureg.ms,
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
    delay_time = params["detect"]["delay_time"]
    on_time = params["detect"]["on_time"]
    off_time = params["detect"]["on_time"]

    rise_delay = 2e-6
    fall_delay = 1e-6

    data_width = on_time - rise_delay - fall_delay

    start_index = delay_time + rise_delay * sample_rate
    #stop_index = start_index +





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
transmissions = np.array(digitizer_data[0])
transmissions = np.reshape(transmissions, (4 * params["repeats"], params["detect"]["repeats"], len(transmissions[0])))
transmissions = np.average(transmissions, axis=1)
#transmissions = np.reshape(transmissions, (4 * params["repeats"], len(transmissions[0][0])))
reflections = np.array(digitizer_data[1])
reflections = np.reshape(reflections, (4 * params["repeats"], params["detect"]["repeats"], len(transmissions[0])))
reflections = np.average(reflections, axis=1)
#reflections = np.reshape(reflections, (4 * params["repeats"], len(reflections[0][0])))

photodiode_times = [kk / sample_rate for kk in range(len(transmissions[0]))]

## plot
#plt.plot(photodiode_times, np.transpose(photodiode_voltages)); plt.legend(); plt.show();

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