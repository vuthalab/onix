import time

import matplotlib.pyplot as plt
import numpy as np
from onix.data_tools import save_experiment_data
from onix.headers.awg.M4i6622 import M4i6622
from onix.headers.pcie_digitizer.pcie_digitizer import Digitizer
from onix.sequences.rf_spectroscopy import RFSpectroscopy
from onix.units import ureg

m4i = M4i6622()

## parameters

params = {
    "wm_channel": 5,
    "repeats": 20,

    "ao": {
        "channel": 0,
        "order": 2,
        "frequency": 80 * ureg.MHz,
        "amplitude": 2000,
        "detect_amplitude": 140,
    },
    "eos": {
        "ac": {
            "channel": 1,
            "amplitude": 500,
            "offset": 0 * ureg.MHz,
        },
        "bb": {
            "channel": 2,
            "amplitude": 500,
            "offset": 0 * ureg.MHz,
        },
        "ca": {
            "channel": 3,
            "amplitude": 500,
            "offset": 0 * ureg.MHz,
        },
    },
    "field_plate": {
        "trigger_channel": 1,
        "output_channel": 1,
        "use": True,
        "voltage": 1 * ureg.V,
        "stark_shift": 1 * ureg.MHz,
    },
    "chasm": {
        "transition": "bb",
        "scan": 1.5 * ureg.MHz,
        "scan_rate": 1 * ureg.MHz / ureg.s,
        "detuning": 0 * ureg.MHz,
    },
    "antihole": {
        "transitions": ["ac", "ca"],
        "scan": 0.6 * ureg.MHz,
        "scan_rate": 1 * ureg.MHz / ureg.s,
        "detuning": 0 * ureg.MHz,
    },
    "detect": {
        "transition": "bb",
        "trigger_channel": 0,
        "detunings": np.linspace(-1, 1, 8) * ureg.MHz,
        "randomize": True,
        "on_time": 10 * ureg.us,
        "off_time": 2 * ureg.us,
        "repeats": 100,
        "fast_repeats": 10,
    },
    "rf": {
        "transition": "ab",
        "trigger_channel": 2,
        "output_channel": 2,
        "offset": 0 * ureg.kHz,
        "detuning": 0 * ureg.kHz,
        "duration": 1 * ureg.ms,
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