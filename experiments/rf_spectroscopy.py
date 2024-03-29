import time

import numpy as np
from onix.sequences.rf_spectroscopy import RFSpectroscopy
from onix.units import ureg
from onix.experiments.shared import (
    m4i,
    dg,
    update_parameters_from_shared,
    setup_digitizer,
    run_sequence,
    save_data,
)


## function to run the experiment
def get_sequence(params):
    sequence = RFSpectroscopy(params)
    return sequence


## parameters
default_params = {
    "name": "RF Spectroscopy",
    "sequence_repeats_per_transfer": 1,
    "data_transfer_repeats": 1,
    "ao": {
        "center_frequency": 75 * ureg.MHz,
    },
    "eos": {
        "ac": {
            "name": "eo_ac",
            "amplitude": 4500,  # 4500
            "offset": -300.0 * ureg.MHz,
        },
        "bb": {
            "name": "eo_bb",
            "amplitude": 1900,  # 1900
            "offset": -300 * ureg.MHz,
        },
        "ca": {
            "name": "eo_ca",
            "amplitude": 1400,  # 1400
            "offset": -300 * ureg.MHz,
        },
    },
    "rf": {
        "amplitude": 0,  # 4200
        "detuning": -65 * ureg.kHz,
        "duration": 0.06 * ureg.ms,
    },
    "chasm": {
        "transitions": ["bb"], #, "rf_both"
        "scan": 2.5 * ureg.MHz,
        "durations": 10 * ureg.ms,
        "repeats": 50,
        "detunings": 0 * ureg.MHz,
        "ao_amplitude": 2000,
    },
    "antihole": {
        "transitions": ["ac", "ca"],
        "durations": [5 * ureg.ms, 5 * ureg.ms],
        "repeats": 50,
        "detunings": 0 * ureg.MHz,
        "ao_amplitude": 2000,
    },
    "detect": {
        "detunings": np.array([-1, -0.5, 0, 0.5, 1]) * ureg.MHz, #np.array([0, 1]) * ureg.MHz,  # np.linspace(-2, 2, 20) * ureg.MHz,
        "ao_amplitude": 450,
        "on_time": 2 * ureg.us,
        "off_time": 0.5 * ureg.us,
        "cycles": {
            "chasm": 0,
            "antihole": 100,
            "rf": 100,
        },
        "delay": 8 * ureg.us,
    },
    "digitizer": {
        "sample_rate": 25e6,
        "ch1_range": 2,
        "ch2_range": 2,
    },
}
default_params = update_parameters_from_shared(default_params)

default_sequence = get_sequence(default_params)
default_sequence.setup_sequence()
setup_digitizer(
    default_sequence.analysis_parameters["digitizer_duration"],
    default_sequence.num_of_record_cycles(),
    default_params["sequence_repeats_per_transfer"],
    ch1_range=default_params["digitizer"]["ch1_range"],
    ch2_range=default_params["digitizer"]["ch2_range"],
)

## test
# params = default_params.copy()
# sequence = get_sequence(params)
# data = run_sequence(sequence, params)
# data_id = save_data(sequence, params, *data)
# print(data_id)

## timeit
start_time = time.time()

## antihole test
params = default_params.copy()
first_data_id = None

for kk in range(30):
    sequence = get_sequence(params)
    data = run_sequence(sequence, params)
    data_id = save_data(sequence, params, *data)
    print(data_id)
    if first_data_id == None:
        first_data_id = data_id

## scan freq
# params = default_params.copy()
# first_data_id = None
#
#
# params["rf"]["duration"] = 1 * ureg.ms
#
# rf_frequencies = np.arange(-300, 300, 10)
# rf_frequencies *= ureg.kHz
# for kk in range(len(rf_frequencies)):
#     params["rf"]["detuning"] = rf_frequencies[kk]
#     sequence = get_sequence(params)
#     data = run_sequence(sequence, params)
#     data_id = save_data(sequence, params, *data)
#     print(data_id)
#     if first_data_id == None:
#         first_data_id = data_id

## scan rf duration
# params = default_params.copy()
# first_data_id = None
#
#
# params["rf"]["duration"] = 1 * ureg.ms
# rf_durations = np.linspace(0.01, 2.0, 15)
# params["rf"]["amplitude"] = 300
# print(rf_durations)
# rf_durations *= ureg.ms
# for kk in range(len(rf_durations)):
#     params["rf"]["duration"] = rf_durations[kk]
#     sequence = get_sequence(params)
#     data = run_sequence(sequence, params)
#     data_id = save_data(sequence, params, *data)
#     print(data_id)
#     if first_data_id == None:
#         first_data_id = data_id

## print info
end_time = time.time()

print("\n")
print(
    f"Took {(end_time-start_time):.2f} s = {(end_time-start_time) / 60:.2f} min = {(end_time-start_time) / 3600:.2f} h"
)
print(f"data = (first, last)")
print(f"\"\": ({first_data_id}, {data_id}),")


## empty