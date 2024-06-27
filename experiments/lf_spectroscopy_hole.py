import time

import numpy as np
from onix.sequences.lf_spectroscopy_hole import LFSpectroscopyHole
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
    sequence = LFSpectroscopyHole(params)
    return sequence


## parameters
default_params = {
    "name": "LF Spectroscopy Hole",
    "sequence_repeats_per_transfer": 1,
    "data_transfer_repeats": 1,
    "ao": {
        "center_frequency": 75 * ureg.MHz,
    },
    "chasm": {
        "transitions": ["ac"],
        "scan": 4 * ureg.MHz,
        "durations": [10 * ureg.ms], # 10 ms
        "repeats": 10,
        "detunings": 0 * ureg.MHz,
        "ao_amplitude": 2000,
    },
    "antihole": {
        "transitions": ["ac", "cb", "rf_b"], #, "rf_b"
        "scan": 2 * ureg.MHz,
        "durations": [6 * ureg.ms, 6 * ureg.ms, 3 * ureg.ms], # [6 * ureg.ms, 6 * ureg.ms, 3 * ureg.ms]
        "repeats": 400, #5
        "detunings": [0 * ureg.MHz, -18 * ureg.MHz, 0 * ureg.MHz],
        "ao_amplitude": 2000, # 2000
        "detect_delay": 0 * ureg.ms,
    },
    "detect": {
        "transition": "ac",
        "detunings": np.linspace(-0.5, 0.5, 5) * ureg.MHz, ##np.flip(np.linspace(-3, 3, 30)) * ureg.MHz, #np.linspace(-0.5, 0.5, 5) * ureg.MHz
        "on_time": 5 * ureg.us,
        "off_time": 1 * ureg.us,
        "cycles": {
            "chasm": 0, # 0
            "antihole": 64, # 64
            "rf": 64, # 64
        },
        "delay": 8 * ureg.us,
        "ao_amplitude": 350,
    },
    "rf": {
        "amplitude": 6000, # 6000
        "T_0": 1 * ureg.ms, # 1 * ureg.ms
        "T_e": 0.5 * ureg.ms, # 0.5 * ureg.ms
        "T_ch": 30 * ureg.ms, # 30 * ureg.ms
        "center_detuning": -60 * ureg.kHz,
        "scan_range": 50 * ureg.kHz,
        "cool_down_time": 0 * ureg.ms,
        "use_hsh": False,
        "pre_lf": False,
    },
    "lf": {
        # "center_frequency": 302 * ureg.kHz, # 168 bbar -- 302 aabar (+- 3)
        # "duration": 0.2 * ureg.ms,
        # "amplitude": 6000,
        "center_frequency": 168 * ureg.kHz, # 168 bbar -- 302 aabar (+- 3)
        "duration": 0.013 * ureg.ms, # 0.013 * ureg.ms
        "amplitude": 6000, # 6000
        "detuning": 0 * ureg.kHz,
        "wait_time": 0.05 * ureg.ms,
        "phase_diff": np.pi / 2,
    },
    "field_plate": {
        "amplitude": 4500 * 1.5,
        "stark_shift": 2 * ureg.MHz * 1.5,
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

## Test HSH Pulse vs Scan
# type = ["HSH", "scan"]
# repeats = 5
# for ll in type:
#     params = default_params.copy()
#     rf_frequencies = np.arange(-200, 200, 20)
#     rf_frequencies *= ureg.kHz
#     if ll == "HSH":
#         params["rf"]["use_hsh"] = True
#     else:
#         params["rf"]["use_hsh"] = False
#     for ii in range(repeats):
#         for kk in range(len(rf_frequencies)):
#             params["rf"]["center_detuning"] = rf_frequencies[kk]
#             sequence = get_sequence(params)
#             data = run_sequence(sequence, params)
#             data_id = save_data(sequence, params, *data)
#             if kk == 0:
#                 first_data_id = data_id
#             elif kk == len(rf_frequencies) - 1:
#                 last_data_id = data_id
#         print(f"{ll}: {first_data_id}, {last_data_id}")

## Scan the LF Detunings
# params = default_params.copy()
# lf_frequencies = np.arange(-15, 15.5, 1)
# lf_frequencies *= ureg.kHz
# for kk in tqdm(range(len(lf_frequencies))):
#     params["lf"]["detuning"] = lf_frequencies[kk]
#     sequence = get_sequence(params)
#     data = run_sequence(sequence, params)
#     data_id = save_data(sequence, params, *data)
#     if kk == 0:
#         first_data_id = data_id
#         print(first_data_id)
#     elif kk == len(lf_frequencies) - 1:
#         last_data_id = data_id
# print(f"({first_data_id}, {last_data_id})")

## Scan the LF Durations
# params = default_params.copy()
# lf_durations = np.arange(0, 0.5, 0.002)
# lf_durations *= ureg.ms
# for kk in tqdm(range(len(lf_durations))):
#     params["lf"]["duration"] = lf_durations[kk]
#     sequence = get_sequence(params)
#     data = run_sequence(sequence, params)
#     data_id = save_data(sequence, params, *data)
#     time.sleep(20)
#     if kk == 0:
#         first_data_id = data_id
#         print(first_data_id)
#     elif kk == len(lf_durations) - 1:
#         last_data_id = data_id
# print(f"({first_data_id}, {last_data_id})")

## Scan the Ramsey phases
# params = default_params.copy()
# phases = np.linspace(0, 2 * np.pi, 10)
# for kk in tqdm(range(len(phases))):
#     params["lf"]["phase_diff"] = phases[kk]
#     sequence = get_sequence(params)
#     data = run_sequence(sequence, params)
#     data_id = save_data(sequence, params, *data)
#     time.sleep(1) # one second delay between each step to prevent heating issues
#     if kk == 0:
#         first_data_id = data_id
#         print(first_data_id)
#     elif kk == len(phases) - 1:
#         last_data_id = data_id
# print(f"({first_data_id}, {last_data_id})")

## Scan the Ramsey frequencies
# params = default_params.copy()
# lf_frequencies = np.arange(-3, 3, 0.3) * ureg.kHz
# for kk in tqdm(range(len(lf_frequencies))):
#     params["lf"]["detuning"] = lf_frequencies[kk]
#     sequence = get_sequence(params)
#     data = run_sequence(sequence, params)
#     data_id = save_data(sequence, params, *data)
#     time.sleep(1) # one second delay between each step to prevent heating issues
#     if kk == 0:
#         first_data_id = data_id
#         print(first_data_id)
#     elif kk == len(lf_frequencies) - 1:
#         last_data_id = data_id
# print(f"({first_data_id}, {last_data_id})")

## Scan the Ramsey wait times
# params = default_params.copy()
# wait_times = np.arange(0.01, 1, 0.05) * ureg.kHz
# for kk in tqdm(range(len(wait_times))):
#     params["lf"]["wait_time"] = wait_times[kk]
#     sequence = get_sequence(params)
#     data = run_sequence(sequence, params)
#     data_id = save_data(sequence, params, *data)
#     time.sleep(1) # one second delay between each step to prevent heating issues
#     if kk == 0:
#         first_data_id = data_id
#         print(first_data_id)
#     elif kk == len(wait_times) - 1:
#         last_data_id = data_id
# print(f"({first_data_id}, {last_data_id})")

## Scan the LF Detunings, bbar, time series (T-violation)
# params = default_params.copy()
# lf_frequencies = np.array([1, -1]) + 0.5
# lf_frequencies *= ureg.kHz
# field_plates = [4500 * 1.5, -4500 * 1.5]
# for ll in range(1000):
#     for mm in field_plates:
#         params["field_plate"]["amplitude"] = mm
#         params["lf"]["phase_diff"] = np.pi / 2
#         for kk in range(len(lf_frequencies)):
#             params["lf"]["detuning"] = lf_frequencies[kk]
#             sequence = get_sequence(params)
#             data = run_sequence(sequence, params)
#             data_id = save_data(sequence, params, *data)
#             print(data_id)
#             if kk == 0:
#                 first_data_id = data_id
#             elif kk == len(lf_frequencies) - 1:
#                 last_data_id = data_id
#         print(f"({first_data_id}, {last_data_id})")
#         params["lf"]["phase_diff"] = -np.pi / 2
#         for kk in range(len(lf_frequencies)):
#             params["lf"]["detuning"] = lf_frequencies[kk]
#             sequence = get_sequence(params)
#             data = run_sequence(sequence, params)
#             data_id = save_data(sequence, params, *data)
#             if kk == 0:
#                 first_data_id = data_id
#             elif kk == len(lf_frequencies) - 1:
#                 last_data_id = data_id
#         print(f"({first_data_id}, {last_data_id})")

## Scan the LF Detunings, bbar, time series (T-violation), fast AWG setup
params = default_params.copy()
lf_frequencies = np.array([1, -1]) + 0.5
lf_frequencies *= ureg.kHz
params["lf"]["detuning"] = lf_frequencies
lf_phases = np.array([np.pi, -np.pi])
params["lf"]["phase_diff"] = lf_phases

sequence = get_sequence(params)
sequence.setup_sequence(use_opposite_field=False, use_rf_index=0)
m4i.setup_sequence(sequence)

opposite_field_plates = [False, True]
lf_indices = list(range(4))
for kk in range(1000000):
    for ll in opposite_field_plates:
        for mm in lf_indices:
            sequence.setup_sequence(ll, mm)
            m4i.setup_sequence_steps_only()
            data = run_sequence(sequence, params, skip_setup=True)
            data_id = save_data(sequence, params, *data)
            if ll == False and mm == 0:
                first_data_id = data_id
            if ll == True and mm == 3:
                last_data_id = data_id
    print(f"({first_data_id}, {last_data_id})")

## ***NOT T-violation***: single LF detuning time series to measure fluctuations
# params = default_params.copy()
# # params["lf"]["detuning"] = -0.5 * ureg.kHz
# # params["lf"]["phase_diff"] = np.pi / 2
#
# sequence = get_sequence(params)
# start_time = time.time()
# data = run_sequence(sequence, params)
# first_data_id = save_data(sequence, params, *data)
#
# for ll in range(1000):
#     # while abs(int((time.time()-start_time)/0.713) - (time.time()-start_time)/0.713) > 0.01:
#     #     pass
#     data = run_sequence(sequence, params, skip_setup=True)
#     data_id = save_data(sequence, params, *data)
#     print(data_id)
#
# print(f"({first_data_id}, {data_id})")