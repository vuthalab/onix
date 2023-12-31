import time

import numpy as np
from onix.data_tools import save_experiment_data
from onix.headers.awg.M4i6622 import M4i6622
from onix.headers.pcie_digitizer.pcie_digitizer import Digitizer
from onix.sequences.antihole_burning import AntiholeBurning
from onix.experiments.helpers import data_averaging
from onix.units import ureg

m4i = M4i6622()
dg = Digitizer()


## parameters
params = {
    "wm_channel": 5,
    "repeats": 2,
    "ao": {
        "name": "ao_dp",
        "order": 2,
        "frequency": 74 * ureg.MHz,
        "amplitude": 2000,
        "detect_amplitude": 650,
        "rise_delay": 1.1 * ureg.us,
        "fall_delay": 0.6 * ureg.us,
    },
    "eos": {
        "ac": {
            "name": "eo_ac",
            "amplitude": 4500,
            "offset": -300 * ureg.MHz,
        },
        "bb": {
            "name": "eo_bb",
            "amplitude": 2000,
            "offset": -300 * ureg.MHz,
        },
        "ca": {
            "name": "eo_ca",
            "amplitude": 1400,
            "offset": -300 * ureg.MHz,
        },
    },
    "chasm": {
        "transition": "bb",
        "scan": 2 * ureg.MHz,
        "scan_rate": 2 * ureg.MHz / ureg.s,
        "detuning": 0 * ureg.MHz,
    },
    "antihole": {
        "transitions": ["ac", "ca"],
        "scan": 0 * ureg.MHz,
        "scan_rate": 0 * ureg.MHz / ureg.s,
        "detuning": 0 * ureg.MHz,
        "duration_no_scan": 0.1 * ureg.s,
        "repeats_one_frequency": 1,
    },
    "detect": {
        "transition": "bb",
        "trigger_channel": 2,
        "detunings": np.linspace(-1., 1, 40) * ureg.MHz,
        "randomize": True,
        "on_time": 10 * ureg.us,
        "off_time": 2 * ureg.us,
        "chasm_repeats": 1,
        "antihole_repeats": 1,
    },
}

## setup sequence
sequence = AntiholeBurning(
    ao_parameters=params["ao"],
    eos_parameters=params["eos"],
    chasm_parameters=params["chasm"],
    antihole_parameters=params["antihole"],
    detect_parameters=params["detect"],
)
sequence.setup_sequence()

## setup the awg
m4i.setup_sequence(sequence)
digitizer_time_s = sequence.analysis_parameters["digitizer_duration"].to("s").magnitude

## setup digitizer
sample_rate = 1e8
dg.set_acquisition_config(
    num_channels=1,
    sample_rate=1e8,
    segment_size=int(digitizer_time_s * sample_rate),
    segment_count=sequence.num_of_records() * params["repeats"]
)
dg.set_channel_config(channel=1, range=2)
dg.set_trigger_source_edge()
dg.write_configs_to_device()

## take data
transmissions = None
dg.start_capture()
time.sleep(0.1)

for kk in range(params["repeats"]):
    print(f"{kk / params['repeats'] * 100:.0f}%")
    m4i.start_sequence()
    m4i.wait_for_sequence_complete()
m4i.stop_sequence()

dg.wait_for_data_ready()
digitizer_sample_rate, digitizer_data = dg.get_data()
transmissions = np.array(digitizer_data[0])

photodiode_times = [kk / sample_rate for kk in range(len(transmissions[0]))]
transmissions_avg, transmissions_err = data_averaging(transmissions, sample_rate, sequence.analysis_parameters["detect_pulse_times"])


## plot transmissions
#import matplotlib.pyplot as plt
#plt.plot(photodiode_times, transmissions[0])
#plt.show()
# add vertical lines showing the detect_pulse_times.

## save data
data = {
    "transmissions_avg": transmissions_avg,
    "transmissions_err": transmissions_err,
}
headers = {
    "params": params,
    "detunings": sequence.analysis_parameters["detect_detunings"]
}
name = "Antihole Burning"
data_id = save_experiment_data(name, data, headers)
print(data_id)

## empty
