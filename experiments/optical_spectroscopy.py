import time

import numpy as np
from onix.sequences.optical_spectroscopy import OpticalSpectroscopy
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
    sequence = OpticalSpectroscopy(params)
    return sequence


## parameters
default_params = {
    "name": "Optical Spectroscopy",
    "sequence_repeats_per_transfer": 10,
    "data_transfer_repeats": 1,
    "chasm": {
        "transitions": ["bb"], #, "rf_both"
        "scan": 3 * ureg.MHz,
        "durations": 10 * ureg.ms,
        "repeats": 20,
        "detunings": 0 * ureg.MHz,
        "ao_amplitude": 2000,
    },
    "antihole": {
        "transitions": ["ac", "ca"],
        "durations": 10 * ureg.ms,
        "repeats": 10,
        "detunings": 0 * ureg.MHz,
        "ao_amplitude": 2000,
    },
    "detect": {
        "detunings": np.linspace(-2, 2, 20) * ureg.MHz,
        "ao_amplitude": 1700,
        "on_time": 3 * ureg.us,
        "off_time": 0.6 * ureg.us,
        "cycles": {
            "chasm": 0,
            "antihole": 16,
            "rf": 16,
        },
    },
    "optical": {
        "transition": "bb",
        "ao_amplitude": 2000,
        "detuning": 1000 * ureg.kHz,
        "duration": 10 * ureg.ms,
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
times = np.linspace(0.1, 50.0, 10) * ureg.ms
for kk in times:
    params["optical"]["duration"] = kk
    sequence = get_sequence(params)
    data = run_sequence(sequence, params)
    data_id = save_data(sequence, params, *data)
    print(data_id)
    if first_data_id == None:
        first_data_id = data_id


## print info
end_time = time.time()

print("\n")
print(
    f"Took {(end_time-start_time):.2f} s = {(end_time-start_time) / 60:.2f} min = {(end_time-start_time) / 3600:.2f} h"
)
print(f"data = (first, last)")
print(f"data = ({first_data_id}, {data_id})")


## empty