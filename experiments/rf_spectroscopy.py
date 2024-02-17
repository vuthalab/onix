import time
from datetime import datetime

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
    sequence = RFSpectroscopy(
        ao_parameters=params["ao"],
        eos_parameters=params["eos"],
        field_plate_parameters=params["field_plate"],
        chasm_parameters=params["chasm"],
        antihole_parameters=params["antihole"],
        rf_parameters=params["rf"],
        detect_parameters=params["detect"],
    )
    return sequence


## parameters
default_params = {
    "name": "RF Spectroscopy",
    "rf": {
        "amplitude": 2000,  # 4200
        "detuning": 0 * ureg.kHz,
        "duration": 0.5 * ureg.ms,
    },
}
default_params = update_parameters_from_shared(default_params)

default_sequence = get_sequence(default_params)
default_sequence.setup_sequence()
setup_digitizer(
    default_sequence.analysis_parameters["digitizer_duration"],
    default_sequence.num_of_records(),
    default_params["sequence_repeats_per_transfer"],
)

## timeit
start_time = time.time()

## scan freq
params = default_params.copy()
first_data_id = None

params["rf"]["amplitude"] = 2000
params["rf"]["duration"] = 0.07 * ureg.ms

rf_frequencies = np.arange(-140, 190, 10)
rf_frequencies *= ureg.kHz
for kk in range(len(rf_frequencies)):
    params["rf"]["detuning"] = rf_frequencies[kk]
    sequence = get_sequence(params)
    data = run_sequence(sequence, params)
    data_id = save_data(sequence, params, *data)
    data_id = save_data()
    print(data_id)
    if first_data_id == None:
        first_data_id = data_id


params["rf"]["amplitude"] = 4200
params["rf"]["duration"] = 0.15 * ureg.ms

rf_frequencies = np.append(np.arange(-300, -140, 10), np.arange(190, 350, 10))
rf_frequencies *= ureg.kHz
for kk in range(len(rf_frequencies)):
    params["rf"]["detuning"] = rf_frequencies[kk]
    sequence = get_sequence(params)
    data = run_sequence(sequence, params)
    data_id = save_data(sequence, params, *data)
    print(data_id)

## print info
end_time = time.time()

print("\n")
print(
    f"Took {(end_time-start_time):.2f} s = {(end_time-start_time) / 60:.2f} min = {(end_time-start_time) / 3600:.2f} h"
)
print(f"data = (first, last)")
print(f"data = ({first_data_id}, {data_id})")

## scan freq

# params = default_params.copy()
# first_data_id = None
#
# params["rf"]["amplitude"] = 2000
# params["rf"]["duration"] = 0.07 * ureg.ms
#
# rf_frequencies = np.arange(-140, 190, 10)
# rf_frequencies *= ureg.kHz
# for kk in range(len(rf_frequencies)):
#     params["rf"]["offset"] = rf_frequencies[kk]
#     data_id = run_experiment(params)
#     print(data_id)
#     if first_data_id == None:
#         first_data_id = data_id
#
#
# params["rf"]["amplitude"] = 4200
# params["rf"]["duration"] = 0.15 * ureg.ms
#
# rf_frequencies = np.append(np.arange(-300, -140, 10), np.arange(190, 350, 10))
# rf_frequencies *= ureg.kHz
# for kk in range(len(rf_frequencies)):
#     params["rf"]["offset"] = rf_frequencies[kk]
#     data_id = run_experiment(params)
#     print(data_id)
#
#
# params = default_params.copy()
# first_data_id = None
#
# rf_frequencies = np.arange(-300, 350, 10)
# rf_frequencies *= ureg.kHz
# for kk in range(len(rf_frequencies)):
#     params["rf"]["offset"] = rf_frequencies[kk]
#     data_id = run_experiment(params)
#     print(data_id)
#     if first_data_id == None:
#         first_data_id = data_id

## scan time
rf_times = np.linspace(0.01, 1, 10) * ureg.ms
params = default_params.copy()
first_data_id = None

for kk in range(len(rf_times)):
    params["rf"]["duration"] = rf_times[kk]
    data_id = run_experiment(params)
    print(data_id)
    if first_data_id == None:
        first_data_id = data_id
        params["first_data_id"] = data_id

## scan antihole and time
# rf_times = np.linspace(0.01, 0.5, 10) * ureg.ms
# antihole_times = np.array([0.03, 0.1, 0.3]) * ureg.s
# params = default_params.copy()
# first_data_id = None
#
# for kk in range(len(rf_times)):
#     params["rf"]["duration"] = rf_times[kk]
#     for antihole_time in antihole_times:
#         params["antihole"]["duration_no_scan"] = antihole_time
#         data_id = run_experiment(params)
#         print(data_id)
#         if first_data_id == None:
#             first_data_id = data_id

## print info
end_time = time.time()

print("\n")
print(f"Took {(end_time-start_time):.2f} s = {(end_time-start_time) / 60:.2f} min = {(end_time-start_time) / 3600:.2f} h")
print(f"data = (first, last)")
print(f"data = ({first_data_id}, {data_id})")

## test


## empty