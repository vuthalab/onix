import time

import numpy as np
from onix.data_tools import save_experiment_data
from onix.units import ureg

from onix.headers.digitizer import DigitizerVisa
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
dg = DigitizerVisa("192.168.0.125")

## parameters

params = {
    "wm_channel": 5,

    "digitizer_channel": 0,
    "rf_channel": 2,

    "repeats": 5,

    "ao": {
        "channel": 0,
        "frequency": 80 * ureg.MHz,
        "amplitude": 1600,
        "detect_amplitude": 140,
    },

    "eo": {
        "channel": 1,
        "offset": 100 * ureg.MHz,
        "amplitude": 3400,
    },

    "detect_ao": {
        "channel": 3,
        "frequency": 80 * ureg.MHz,
        "amplitude": 2000,
    },

    "burn": {
        "transition": "bb",
        "duration": 2 * ureg.s,
        "scan": 1 * ureg.MHz,
        "detuning": 0 * ureg.MHz,
    },

    "repop": {
        "transitions": ["ac", "cb"],
        "duration": 1 * ureg.s,
        "scan": 0.5 * ureg.MHz,
        "detuning": 0 * ureg.MHz,
    },

    "flop": {
        "transition": "ab",
        "duration": 10 * ureg.ms,
        "amplitude": 10000,
        "repeats": 10,
    },

    "detect": {
        "transition": "bb",
        "detunings": np.linspace(-2, 2, 31) * ureg.MHz,
        "on_time": 16 * ureg.us,
        "off_time": 8 * ureg.us,
        "repeats": 5,
        "ttl_probe_offset_time": 4 * ureg.us,
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

sample_rate = 1e7
dg.configure_acquisition(
    sample_rate=sample_rate,
    samples_per_record=int(sequence.detect_time.to("s").magnitude * sample_rate),
    num_records=sequence.num_of_records(),
)
dg.configure_channels(channels=[1, 2], voltage_range=2)
dg.set_trigger_source_external()
dg.set_arm(triggers_per_arm=sequence.num_of_records())

## take data
epoch_times = []
transmissions = None
reflections = None

for kk in range(params["repeats"]):
    dg.initiate_data_acquisition()
    time.sleep(0.1)
    m4i.start_sequence()
    epoch_times.append(time.time())
    m4i.wait_for_sequence_complete()
    time.sleep(0.1)
    voltages = dg.get_waveforms([1], records=(1, sequence.num_of_records()))
    if transmissions is None:
        transmissions = voltages[0]
        reflections = voltages[1]
    else:
        transmissions = np.append(transmissions, voltages[0], axis=0)
        reflections = np.append(reflections, voltages[1], axis=0)
m4i.stop_sequence()

photodiode_times = [kk / sample_rate for kk in range(len(transmissions[0]))]

## plot
#plt.plot(photodiode_times, np.transpose(photodiode_voltages)); plt.legend(); plt.show();

## save data
data = {
    "times": photodiode_times,
    "transmissions": transmissions,
    "reflections": reflections,
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