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
    "sequence_repeats_per_transfer": 20,
    "data_transfer_repeats": 1,
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
        "detuning": 0 * ureg.kHz,
        "duration": 0.5 * ureg.ms,
    },
    "antihole": {
        "transitions": ["ac", "ca"],
        "durations": 10 * ureg.ms,
        "repeats": 0,
        "detunings": 0 * ureg.MHz,
        "ao_amplitude": 2000,
    },
    "detect": {
        "detunings": np.array([0.0, 2.0]) * ureg.MHz, # np.linspace(-2, 2, 20) * ureg.MHz, #
        "ao_amplitude": 1000,
        "on_time": 3 * ureg.us,
        "off_time": 0.6 * ureg.us,
        "cycles": {
            "chasm": 0,
            "antihole": 40,
            "rf": 40,
        },
    },
    "digitizer": {
        "sample_rate": 25e6,
        "ch1_range": 2,
        "ch2_range": 0.5,
    },
}
default_params = update_parameters_from_shared(default_params)

default_sequence = get_sequence(default_params)
default_sequence.setup_sequence()
setup_digitizer(
    default_sequence.analysis_parameters["digitizer_duration"],
    default_sequence.num_of_record_cycles(),
    default_params["sequence_repeats_per_transfer"],
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
for kk in range(50):
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
# params["rf"]["amplitude"] = 2000
# params["rf"]["duration"] = 4 * ureg.ms
#
# rf_frequencies = np.arange(-300, 300, 20)
# rf_frequencies *= ureg.kHz
# for kk in range(len(rf_frequencies)):
#     params["rf"]["detuning"] = rf_frequencies[kk]
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
print(f"data = ({first_data_id}, {data_id})")


## empty