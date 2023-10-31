import time

import numpy as np
from onix.data_tools import save_experiment_data
from onix.units import ureg

from onix.headers.pcie_digitizer.pcie_digitizer import Digitizer
from onix.headers.wavemeter.wavemeter import WM
from onix.headers.awg.M4i6622 import M4i6622
from onix.sequences.rf_ramsey import RFRamsey
import matplotlib.pyplot as plt
import sys

#phase = float(sys.argv[1])
phase = 0

wavemeter = WM()

def wavemeter_frequency():
    freq = wavemeter.read_frequency(params["wm_channel"])
    if isinstance(freq, str):
        return -1
    return freq

m4i = M4i6622()

## parameters

params = {
    "wm_channel": 5,

    "digitizer_channel": 0,
    "field_plate_channel": 1,
    "rf_channel": 2,

    "repeats": 2,

    "ao": {
        "channel": 0,
        "frequency": 80 * ureg.MHz,
        "amplitude": 2000,
        "detect_amplitude": 90,
    },

    "eo": {
        "channel": 1,
        "offset": 60 * ureg.MHz,
        "amplitude": 3400,
    },

    "detect_ao": {
        "channel": 3,
        "frequency": 80 * ureg.MHz,
        "amplitude": 0,
    },

    "burn": {
        "transition": "bb",
        "duration": 5 * ureg.s,
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
        "pulse_time": 0.2 * ureg.ms,
        "wait_time": 0.2 * ureg.ms,
        "amplitude": 6000,  # do not go above 6000.
        "phase_difference": phase,
        "offset": 35 * ureg.kHz,
        "repeats": 1,
    },

    "detect": {
        "transition": "bb",
        "detunings": np.linspace(-2.5, 2.5, 51) * ureg.MHz,
        "on_time": 16 * ureg.us,
        "off_time": 8 * ureg.us,
        "delay_time": 600 * ureg.ms,
        "repeats": 500,
        "ttl_detect_offset_time": 4 * ureg.us,
        "ttl_start_time": 12 * ureg.us,
        "ttl_duration": 4 * ureg.us,
    },
}
print(f"phase is {params['flop']['phase_difference']}")

## setup sequence
sequence = RFRamsey(
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

## take data
sample_rate = 1e8
dg = Digitizer(False)
val = dg.configure_system(
    mode=2,
    sample_rate=int(sample_rate),
    segment_size=64,
    segment_count=sequence.num_of_records(),
)

acq_params = dg.get_acquisition_parameters()

epoch_times = []
transmissions = None
reflections = None

for kk in range(params["repeats"]):
    dg.arm_digitizer()
    time.sleep(0.1)
    print(f"{kk / params['repeats'] * 100:.0f}%")
    m4i.start_sequence()
    epoch_times.append(time.time())
    m4i.wait_for_sequence_complete()
    digitizer_data = dg.get_data()
    current_rep_transmissions = np.array(digitizer_data[0])
    current_rep_transmissions = np.reshape(current_rep_transmissions, (4, params["detect"]["repeats"], len(current_rep_transmissions[0])))
    current_rep_transmissions = np.average(current_rep_transmissions, axis=1)
    current_rep_reflections = np.array(digitizer_data[1])
    current_rep_reflections = np.reshape(current_rep_reflections, (4, params["detect"]["repeats"], len(current_rep_reflections[0])))
    current_rep_reflections = np.average(current_rep_reflections, axis=1)
    if transmissions is None:
        transmissions = current_rep_transmissions
        reflections = current_rep_reflections
    else:
        transmissions = np.append(transmissions, current_rep_transmissions, axis=0)
        reflections = np.append(reflections, current_rep_reflections, axis=0)
m4i.stop_sequence()

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
name = "RF Ramsey"
data_id = save_experiment_data(name, data, headers)
print(data_id)

## empty