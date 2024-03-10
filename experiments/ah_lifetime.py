import time

import numpy as np
from onix.sequences.ah_lifetime import AHLifetime
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
    sequence = AHLifetime(params)
    return sequence


## parameters
default_params = {
    "name": "AH Lifetime",
    "detect": {
        "detunings": np.linspace(-2, 2, 20) * ureg.MHz,
        "ao_amplitude": 1700,
        "on_time": 3 * ureg.us,
        "off_time": 0.6 * ureg.us,
        "delta_detect_time": 0 * ureg.s,
        "cycles": {
            "chasm": 0,
            "antihole": 16,
            "antihole_delay": 16,
            "rf": 0,
        },
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


## timeit
start_time = time.time()

## scan delta detect times
params = default_params.copy()
first_data_id = None

delta_detect_times = np.logspace(-3, 4, num = 50) * ureg.s
#delta_detect_times = [3600 * ureg.s]
for delta_detect_time in delta_detect_times:
    params["detect"]["delta_detect_time"] = delta_detect_time

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