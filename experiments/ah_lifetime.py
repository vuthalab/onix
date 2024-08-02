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
    "sequence_repeats_per_transfer": 1,
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
    "chasm": {
        "transitions": ["bb"], #, "rf_both"
        "scan": 3 * ureg.MHz,
        "durations": 100 * ureg.us,
        "repeats": 4000,
        "detunings": 0 * ureg.MHz,
        "ao_amplitude": 2000,
    },
    "antihole": {
        "transitions": ["ac", "ca"], #, "rf_b" (for rf assist)
        "durations": [100 * ureg.us, 100 * ureg.us],
        "repeats": 2000,
        "ao_amplitude": 2000,
        "blue_light": {
            "use": True,
            "amplitude": 7000,
        }
    },
    "detect": {
        "detunings": np.linspace(-2, 2, 12) * ureg.MHz, # np.array([-2, 0]) * ureg.MHz,
        "on_time": 5 * ureg.us, #5
        "off_time": 0.5 * ureg.us,
        "delta_detect_time": 0 * ureg.s,
        "ao_amplitude": 180,
        "cycles": {
            "chasm": 0,
            "antihole": 32,
            "antihole_delay": 32,
            "rf": 0,
        },
    },
    "rf": {
        "amplitude": 0,
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

delta_detect_times = np.logspace(0.01, 1.1, num = 30)  * ureg.s
#delta_detect_times = [3600 * ureg.s]
for delta_detect_time in delta_detect_times:
    params["detect"]["delta_detect_time"] = delta_detect_time

    sequence = get_sequence(params)
    data = run_sequence(sequence, params)
    data_id = save_data(sequence, params, *data)
    print(data_id)
    if first_data_id == None:
        first_data_id = data_id

## scan delta detect times and rf power
# params = default_params.copy()
# first_data_id = None
#
# time.sleep(3000)
# delta_detect_times = np.logspace(0, 3, num = 15) * ureg.s
# #delta_detect_times = [3600 * ureg.s]
# for kk in np.linspace(0, 1000, 10):
#     params["rf"]["amplitude"] = kk
#     for delta_detect_time in delta_detect_times:
#         params["detect"]["delta_detect_time"] = delta_detect_time
#
#         sequence = get_sequence(params)
#         data = run_sequence(sequence, params)
#         data_id = save_data(sequence, params, *data)
#         print(data_id)
#         if first_data_id == None:
#             first_data_id = data_id

## print info
end_time = time.time()

print("\n")
print(
    f"Took {(end_time-start_time):.2f} s = {(end_time-start_time) / 60:.2f} min = {(end_time-start_time) / 3600:.2f} h"
)
print(f"data = (first, last)")
print(f"data = ({first_data_id}, {data_id})")

## empty