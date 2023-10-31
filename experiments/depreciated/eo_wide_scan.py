import time

import numpy as np
from onix.data_tools import save_experiment_data
from onix.units import ureg

from onix.headers.digitizer import DigitizerVisa
from onix.headers.wavemeter.wavemeter import WM
from onix.headers.awg.M4i6622 import M4i6622
from onix.sequences.eo_wide_scan import EOWideScan
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
    "repeats": 2,

    "ao": {
        "channel": 0,
        "frequency": 80 * ureg.MHz,
        "amplitude": 2000,
        "detect_amplitude": 140,
    },

    "eo": {
        "channel": 1,
        "offset": 0 * ureg.MHz,
        "amplitude": 1700,
    },

    "detect_ao": {
        "channel": 3,
        "frequency": 80 * ureg.MHz,
        "amplitude": 2000,
    },

    "sweep": {
        "duration": 20 * ureg.s,
        "scan": 300 * ureg.MHz,
        "detuning": 150 * ureg.MHz,
    },

    "burn": {
        "duration": 5 * ureg.s,
        "scan": 2 * ureg.MHz,
        "detuning": 115.25 * ureg.MHz,
    },

    "burn1": {
        "duration": 5 * ureg.s,
        "scan": 2 * ureg.MHz,
        "detuning": 100 * ureg.MHz,
    },

    "flop": {
        "transition": "ab",
        "duration": 20 * ureg.ms,
        "amplitude": 0,
        "offset": 25 * ureg.kHz,
        "scan": 2 * ureg.kHz,
        "repeats": 1,
    },

    "detect": {
        "detunings": np.linspace(-10, 330, 800) * ureg.MHz,
        "on_time": 10 * ureg.us,
        "off_time": 4 * ureg.us,
        "repeats": 1,
        "ttl_detect_offset_time": 4 * ureg.us,
        "ttl_start_time": 12 * ureg.us,
        "ttl_duration": 4 * ureg.us,
    },
}

## setup sequence
sequence = EOWideScan(
    ao_parameters=params["ao"],
    eo_parameters=params["eo"],
    detect_ao_parameters=params["detect_ao"],
    sweep_parameters=params["sweep"],
    burn_parameters=params["burn"],
    burn1_parameters=params["burn1"],
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
    voltages = dg.get_waveforms([1, 2], records=(1, sequence.num_of_records()))
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
    "monitors": reflections,
    "epoch_times": epoch_times,
}
headers = {
    "params": params,
    "wavemeter_frequency": wavemeter_frequency(),
}
name = "EO Wide Scan"
data_id = save_experiment_data(name, data, headers)
print(data_id)

## empty