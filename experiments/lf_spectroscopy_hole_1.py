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
    "sequence_repeats_per_transfer": 20,
    "data_transfer_repeats": 1,
    "ao": {
        "name": "ao_dp",
        "order": 2,
        "center_frequency": 75 * ureg.MHz,
        "rise_delay": 1.1 * ureg.us,
        "fall_delay": 0.6 * ureg.us,
    },
    "eos": {
        "ac": {
            "amplitude": 0,  # 4500
        },
        "bb": {
            "amplitude": 0,  # 1900
        },
        "ca": {
            "amplitude": 0,  # 1400
        },
    },
    "pre_chasm": {
        "transitions": ["bb"],
        "scan": 4 * ureg.MHz,
        "durations": [10 * ureg.ms],
        "repeats": 10,
        "detunings": 0 * ureg.MHz,
        "ao_amplitude": 2000,
    },
    "chasm": {
        "scan": 2.5 * ureg.MHz,
        "ac_duration": 6 * ureg.ms,
        "ca_duration": 6 * ureg.ms,  # actually cb
        "rf_duration": 3 * ureg.ms,
        "repeats": 10,
        "detunings": 0 * ureg.MHz,
        "ao_amplitude": 2000,
    },
    "detect": {
        "transition": "bb",
        "detunings": np.flip(np.linspace(-0.5, 0.5, 5)) * ureg.MHz, #(np.linspace(-0.2, 0.2, 5)) * ureg.MHz,
        "on_time": 5 * ureg.us,
        "off_time": 1 * ureg.us,
        "cycles": {
            "chasm": 0,
            "antihole": 64,
            "rf": 64,
        },
        "delay": 8 * ureg.us,
        "ao_amplitude": 350,
    },
    "rf": {
        "amplitude": 6000,
        "T_0": 1 * ureg.ms,
        "T_e": 0.5 * ureg.ms,
        "T_ch": 30 * ureg.ms,
        "center_detuning": -60 * ureg.kHz,
        "scan_range": 50 * ureg.kHz,
        "cool_down_time": 0 * ureg.ms,
        "use_hsh": True,
        "pre_lf": False,
    },
    "lf": {
        # "center_frequency": 302 * ureg.kHz, # 168 bbar -- 302 aabar (+- 3)
        # "duration": 0.2 * ureg.ms,
        # "amplitude": 6000,
        "center_frequency": 168 * ureg.kHz, # 168 bbar -- 302 aabar (+- 3)
        "duration": 0.013 * ureg.ms,
        "amplitude": 6000,
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
# lf_durations = np.arange(0, 0.05, 0.002)
# lf_durations *= ureg.ms
# for kk in tqdm(range(len(lf_durations))):
#     params["lf"]["duration"] = lf_durations[kk]
#     sequence = get_sequence(params)
#     data = run_sequence(sequence, params)
#     data_id = save_data(sequence, params, *data)
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
#     if kk == 0:
#         first_data_id = data_id
#         print(first_data_id)
#     elif kk == len(phases) - 1:
#         last_data_id = data_id
# print(f"({first_data_id}, {last_data_id})")

## Scan the Ramsey frequencies
# params = default_params.copy()
# lf_frequencies = np.arange(-7, 7, 0.7) * ureg.kHz
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
# wait_times = np.arange(0.01, 1, 0.05) * ureg.ms
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

## Scan the LF Detunings, bbar, time series
# params = default_params.copy()
# lf_frequencies = np.arange(-15, 15.5, 1.5)
# lf_frequencies *= ureg.kHz
# field_plates = [default_params["field_plate"]["amplitude"], -default_params["field_plate"]["amplitude"]]
# for ll in range(1000):
#     for mm in field_plates:
#         params["field_plate"]["amplitude"] = mm
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
#         for kk in range(len(lf_frequencies)):
#             params["lf"]["detuning"] = lf_frequencies[len(lf_frequencies)-kk -1]
#             sequence = get_sequence(params)
#             data = run_sequence(sequence, params)
#             data_id = save_data(sequence, params, *data)
#             if kk == 0:
#                 first_data_id = data_id
#             elif kk == len(lf_frequencies) - 1:
#                 last_data_id = data_id
#         print(f"({first_data_id}, {last_data_id})")

## Scan the LF Detunings, bbar, time series
params = default_params.copy()
lf_frequencies = np.array([1, -1])
lf_frequencies *= ureg.kHz
field_plates = [default_params["field_plate"]["amplitude"], -default_params["field_plate"]["amplitude"]]
for ll in range(1000):
    for mm in field_plates:
        params["field_plate"]["amplitude"] = mm
        params["lf"]["phase_diff"] = np.pi / 2
        for kk in range(len(lf_frequencies)):
            params["lf"]["detuning"] = lf_frequencies[kk]
            sequence = get_sequence(params)
            data = run_sequence(sequence, params)
            data_id = save_data(sequence, params, *data)
            print(data_id)
            if kk == 0:
                first_data_id = data_id
            elif kk == len(lf_frequencies) - 1:
                last_data_id = data_id
        print(f"({first_data_id}, {last_data_id})")
        params["lf"]["phase_diff"] = -np.pi / 2
        for kk in range(len(lf_frequencies)):
            params["lf"]["detuning"] = lf_frequencies[kk]
            sequence = get_sequence(params)
            data = run_sequence(sequence, params)
            data_id = save_data(sequence, params, *data)
            if kk == 0:
                first_data_id = data_id
            elif kk == len(lf_frequencies) - 1:
                last_data_id = data_id
        print(f"({first_data_id}, {last_data_id})")