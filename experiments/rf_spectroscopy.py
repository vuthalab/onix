import time

import numpy as np
from onix.data_tools import save_experiment_data
from onix.units import ureg

from onix.headers.pcie_digitizer.pcie_digitizer import Digitizer
from onix.headers.wavemeter.wavemeter import WM
from onix.headers.awg.M4i6622 import M4i6622
from onix.sequences.rf_spectroscopy import RFSpectroscopy
import matplotlib.pyplot as plt

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
    "rf_channel": 2,

    "repeats": 20,

    "ao": {
        "channel": 0,
        "frequency": 80 * ureg.MHz,
        "amplitude": 2000,
        "detect_amplitude": 140,
    },

    "eo": {
        "channel": 1,
        "offset": 100 * ureg.MHz,
        "amplitude": 24000,
    },

    "detect_ao": {
        "channel": 3,
        "frequency": 80 * ureg.MHz,
        "amplitude": 0,
    },

    "burn": {
        "transition": "bb",
        "duration": 1.5 * ureg.s,
        "scan": 3 * ureg.MHz,
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
        "step_frequency": 2 * ureg.kHz,
        "step_time": 1 * ureg.ms,
        "on_time": 1 * ureg.ms,
        "amplitude": 6000,  # do not go above 6000.
        "offset": 30 * ureg.kHz,
        "scan": 20 * ureg.kHz,
        "repeats": 1,
    },

    "detect": {
        "transition": "bb",
        "detunings": np.linspace(-1.1, 1.1, 56) * ureg.MHz,
        "on_time": 16 * ureg.us,
        "off_time": 8 * ureg.us,
        "delay_time": 600 * ureg.ms,
        "repeats": 1,
        "ttl_detect_offset_time": 4 * ureg.us,
        "ttl_start_time": 12 * ureg.us,
        "ttl_duration": 4 * ureg.us,
    },
}

## setup sequence
sequence = RFSpectroscopy(
    ao_parameters=params["ao"],
    eo_parameters=params["eo"],
    detect_ao_parameters=params["detect_ao"],
    burn_parameters=params["burn"],
    repop_parameters=params["repop"],
    flop_parameters=params["flop"],
    detect_parameters=params["detect"],
    digitizer_channel=params["digitizer_channel"],
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
    sample_rate=sample_rate,
    segment_size=int(sequence.detect_time.to("s").magnitude * sample_rate),
    segment_count=sequence.num_of_records() * params['repeats'],
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
reflections = np.array(digitizer_data[1])

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
name = "RF Spectroscopy"
data_id = save_experiment_data(name, data, headers)
print(data_id)

## empty