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
from tqdm import tqdm


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
        "amplitude": 4200,  # 4200
        "detuning": (65) * ureg.kHz,
        "duration": 0.1 * ureg.ms,
    },
    "chasm": {
        "transitions": ["bb"], #, "rf_both"
        "scan": 3.5 * ureg.MHz,
        "durations": 50 * ureg.us,
        "repeats": 500,
        "detunings": 0 * ureg.MHz,
        "ao_amplitude": 2000,
    },
    "antihole": {
        "transitions": ["ac", "ca"], #, "rf_b" (for rf assist)
        "durations": [0.1 * ureg.ms, 0.1 * ureg.ms],
        "repeats": 200,
        "ao_amplitude": 800,
    },
    "detect": {
        "detunings": np.linspace(-3.5, 3.5, 10) * ureg.MHz, # np.array([-2, 0]) * ureg.MHz,
        "on_time": 5 * ureg.us,
        "off_time": 0.5 * ureg.us,
        "cycles": {
            "chasm": 0,
            "antihole": 64,
            "rf": 64,
        },
        "delay": 8 * ureg.us,
    },
    "digitizer": {
        "sample_rate": 25e6,
        "ch1_range": 2,
        "ch2_range": 2,
    },
    "field_plate": {
        "amplitude": 3800 * 3,
        "stark_shift": 2.2 * 3 * ureg.MHz,
        "use": True,
    }
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
# params = default_params.copy()
# first_data_id = None
#
# for kk in range(100):
#     sequence = get_sequence(params)
#     data = run_sequence(sequence, params)
#     data_id = save_data(sequence, params, *data)
#     print(data_id)
#     if first_data_id == None:
#         first_data_id = data_id

## scan freq
# params = default_params.copy()
# first_data_id = None
#
#
# # params["rf"]["duration"] = 1 * ureg.ms
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

## scan inhom broad
params = default_params.copy()
first_data_id = None

rf_frequencies = np.arange(-150, 160, 15)
rf_frequencies *= ureg.kHz
for mm in range(100):
    for ll in [-3800 * 3, 3800 * 3]:
        params["field_plate"]["amplitude"] = ll
        for kk in range(len(rf_frequencies)):
            params["rf"]["detuning"] = rf_frequencies[kk] + 5 * ureg.kHz
            sequence = get_sequence(params)
            data = run_sequence(sequence, params)
            data_id = save_data(sequence, params, *data)
            print(data_id)
            if first_data_id == None:
                first_data_id = data_id

## scan power
# params = default_params.copy()
# first_data_id = None
#
# rf_amplitudes = np.sqrt(np.linspace(0, 4000 ** 2, 25))
# for kk in range(len(rf_amplitudes)):
#     params["rf"]["amplitude"] = rf_amplitudes[kk]
#     sequence = get_sequence(params)
#     data = run_sequence(sequence, params)
#     data_id = save_data(sequence, params, *data)
#     print(data_id)
#     if first_data_id == None:
#         first_data_id = data_id

## scan rf duration
# for amp in [3800, -3800]:
#     start_time = time.time()
#     params = default_params.copy()
#     first_data_id = None
#
#     rf_durations = np.linspace(0.01, 0.75, 25)
#     rf_durations *= ureg.ms
#     params["field_plate"]["amplitude"] = amp
#     for kk in range(len(rf_durations)):
#         params["rf"]["duration"] = rf_durations[kk]
#         sequence = get_sequence(params)
#         data = run_sequence(sequence, params)
#         data_id = save_data(sequence, params, *data)
#         #print(data_id)
#         if first_data_id == None:
#             first_data_id = data_id
#     end_time = time.time()
#
#     print(amp)
#     print("\n")
#     print(
#         f"Took {(end_time-start_time):.2f} s = {(end_time-start_time) / 60:.2f} min = {(end_time-start_time) / 3600:.2f} h"
#     )
#     print(f"data = (first, last)")
#     print(f"\"\": ({first_data_id}, {data_id}),")



## chasm test
# params = default_params.copy()
#
# params["chasm"]["durations"] = 10 * ureg.ms
# params["chasm"]["repeats"] = 50
# params["chasm"]["ao_amplitude"] = 2000
#
# # run once with chasm burning
# sequence = get_sequence(params)
# data = run_sequence(sequence, params)
# first_data_id = save_data(sequence, params, *data)
#
# # rerun without chasm burning
# params["chasm"]["durations"] = 1e-6 * ureg.ms
# params["chasm"]["repeats"] = 0
# params["chasm"]["ao_amplitude"] = 0
#
# for kk in tqdm(range(99)):
#     sequence = get_sequence(params)
#     data = run_sequence(sequence, params)
#     data_id = save_data(sequence, params, *data)


## print info
end_time = time.time()

print("\n")
print(
    f"Took {(end_time-start_time):.2f} s = {(end_time-start_time) / 60:.2f} min = {(end_time-start_time) / 3600:.2f} h"
)
print(f"data = (first, last)")
print(f"\"\": ({first_data_id}, {data_id}),")


## empty
