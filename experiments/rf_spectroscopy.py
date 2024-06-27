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
from onix.headers.quarto_frequency_lock import Quarto as f_lock_Quarto

from onix.headers.pulse_tube import PulseTube

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
        "transition": "bc",
        "amplitude": 8000,  # 4200
        "detuning": (65) * ureg.kHz,
        "duration": 2 * ureg.ms,
    },
    "chasm": {
        "transitions": ["bb"], #, "rf_both"
        "scan": 3 * ureg.MHz,
        "durations": 1000 * ureg.us,
        "repeats": 50,
        "detunings": 0 * ureg.MHz,
        "ao_amplitude": 2000,
    },
    "antihole": {
        "transitions": ["ac", "ca"], #, "rf_b" (for rf assist)
        "durations": [1000 * ureg.us, 1000 * ureg.us],
        "repeats": 100,
        "ao_amplitude": 2000,
    },
    "detect": {
        "transition": "bb",
        "detunings": (np.linspace(-2.5, 2.5, 20)) * ureg.MHz, #np.array([-2, 0]) * ureg.MHz, #  # np.array([-2, 0]) * ureg.MHz,
        "on_time": 5 * ureg.us, #5
        "off_time": 1 * ureg.us,
        "cycles": {
            "chasm": 0,
            "antihole": 32,
            "rf": 32,
        },
        "delay": 8 * ureg.us,
        "ao_amplitude": 350,
    },
    "field_plate": {
        "amplitude": 4500 * 1.,
        "stark_shift": 2 * ureg.MHz * 1.,
        "use": False,
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

## timeit
start_time = time.time()
first_data_id = None

## test
# params = default_params.copy()
# for ii in range(1):
#     sequence = get_sequence(params)
#     data = run_sequence(sequence, params)
#     data_id = save_data(sequence, params, *data)
#     print(data_id)

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
params = default_params.copy()
first_data_id = None
rf_frequencies = np.linspace(-240, -60, 25)
rf_frequencies *= ureg.kHz
# f_check = f_lock_Quarto(location='/dev/ttyACM0')
# field_plate_amplitude = 4500

for _ in tqdm(range(1)):
    # for run_n, amplitude in [(1, field_plate_amplitude), (2, -field_plate_amplitude)]:
    # print(run_n)
    # params["field_plate"]["amplitude"] = amplitude
    # expt_start_time = time.time()
    for kk in range(len(rf_frequencies)):

        # print_unlock = False
        # while True:
        #     if f_check.get_last_transmission_point() > 0.1:
        #         break
        #     if print_unlock == False:
        #         print("LASER UNLOCKED")
        #         print_unlock = True
        #



        params["rf"]["detuning"] = rf_frequencies[kk]
        sequence = get_sequence(params)
        data = run_sequence(sequence, params)
        data_id = save_data(sequence, params, *data)
        if _ == 0:
            print(data_id)
        if first_data_id == None:
            first_data_id = data_id

    expt_end_time = time.time()
    print(f"time taken for one iteration: {expt_end_time-expt_start_time}")
    print(data_id)

## scan inhom broad
# params = default_params.copy()
# first_data_id = None
#
# detuning_offsets = np.arange(-0.5, 0.6, 0.1) * ureg.MHz
# for kk in range(len(detuning_offsets)):
#     print(detuning_offsets[kk])
#     params["detect"]["detunings"] = np.linspace(-2, 2, 10) * ureg.MHz + detuning_offsets[kk]
#     rf_frequencies = np.arange(-150, 160, 15)
#     rf_frequencies *= ureg.kHz
#     for mm in range(30):
#         for ll in [-3800 * 2, 3800 * 2]:
#             params["field_plate"]["amplitude"] = ll
#             for kk in range(len(rf_frequencies)):
#                 params["rf"]["detuning"] = rf_frequencies[kk]
#                 sequence = get_sequence(params)
#                 data = run_sequence(sequence, params)
#                 data_id = save_data(sequence, params, *data)
#                 #print(data_id)
#                 if first_data_id == None:
#                     first_data_id = data_id
#     print(data_id + 1)

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
# start_time = time.time()
# params = default_params.copy()
# first_data_id = None
#
# for _ in range(1):
#     rf_durations = np.linspace(0.01, 5, 200)
#     rf_durations *= ureg.ms
#     for kk in range(len(rf_durations)):
#         params["rf"]["duration"] = rf_durations[kk]
#         sequence = get_sequence(params)
#         data = run_sequence(sequence, params)
#         data_id = save_data(sequence, params, *data)
#         print(data_id)
#         if first_data_id == None:
#             first_data_id = data_id
#     end_time = time.time()
#
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
