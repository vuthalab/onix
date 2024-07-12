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
from onix.headers.unlock_check import run_expt_check_lock


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
        "repeats": 30, #100,
        "detunings": 0 * ureg.MHz,
        "ao_amplitude": 2000,
    },
    "antihole": {
        "transitions": ["ac", "cb", "rf_b"], #, "rf_b"
        "scan": 2 * ureg.MHz,
        "durations": [6 * ureg.ms, 6 * ureg.ms, 3 * ureg.ms], # [6 * ureg.ms, 6 * ureg.ms, 3 * ureg.ms]
        "repeats": 100, #5 100
        "detunings": [0 * ureg.MHz, -18 * ureg.MHz, 0 * ureg.MHz],
        "ao_amplitude": 2000, # 2000
        "detect_delay": 0 * ureg.ms,
        "use_hsh": False,
    },
    "detect": {
        "transition": "ac",
        "detunings": np.linspace(-0.5, 0.5, 5) * ureg.MHz, #np.flip(np.linspace(-3, 3, 30)) * ureg.MHz, #np.linspace(-0.5, 0.5, 5) * ureg.MHz
        "on_time": 5 * ureg.us,
        "off_time": 1 * ureg.us,
        "cycles": {
            "chasm": 0,
            "antihole": 0,
            "rf": 16,
            #"lf": 64,
        },
        "delay": 8 * ureg.us,
        "ao_amplitude": 500,
        "simultaneous": False,
    },
    "rf": {
        "amplitude": 6000,
        "T_0": 1 * ureg.ms,
        "T_e": 0.5 * ureg.ms,
        "T_ch": 30 * ureg.ms,
        "center_detuning": -52 * ureg.kHz,
        # "center_detuning1": 60 * ureg.kHz,
        # "center_detuning2": -60 * ureg.kHz,
        "scan_range": 50 * ureg.kHz,
        "cool_down_time": 0 * ureg.ms,
        "use_hsh": False,
        "pre_lf": False,
    },
    "lf": {
        "center_frequency": 140 * ureg.kHz, # 168 bbar -- 302 aabar (+- 3)
        "duration": 0.025 * ureg.ms,
        "amplitude": 1500,

        # bbar --
        # "center_frequency": 141.3 * ureg.kHz, # 168 bbar -- 302 aabar (+- 3)
        # "duration": 0.25 * ureg.ms,
        # "amplitude": 150,

        # aabar -- amplitude * duration = 545 ms for aabar pi-pulse
        # "center_frequency": 251 * ureg.kHz, # 168 bbar -- 302 aabar (+- 3)
        # "duration": 0.06 * ureg.ms, # 0.013 * ureg.ms
        # "amplitude": 8000, # 940, # 6000

        "detuning": 0 * ureg.kHz,
        "wait_time": 0.05 * ureg.ms,
        "phase_diff": 0,
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

## Scan the LF Detunings
params = default_params.copy()
lf_frequencies = np.arange(-30, 30, 1)
# np.random.shuffle(lf_frequencies)
lf_frequencies *= ureg.kHz
for ll in [False, True]:
    sequence = get_sequence(params)
    sequence.setup_sequence(use_opposite_field=ll)
    m4i.setup_sequence(sequence)
    for kk in tqdm(range(len(lf_frequencies))):
        params["lf"]["detuning"] = lf_frequencies[kk]
        del sequence._segments["lf"]
        sequence._define_lf()
        m4i.change_segment("lf")
        m4i.setup_sequence_steps_only()
        m4i.write_all_setup()
        def worker():
            start_time = time.time()
            data = run_sequence(sequence, params, skip_setup=True)
            return (start_time, data)
        start_time, data = run_expt_check_lock(worker)
        data_id = save_data(sequence, params, *data)
        if kk == 0:
            first_data_id = data_id
            print(first_data_id)
        elif kk == len(lf_frequencies) - 1:
            last_data_id = data_id
    print(f"({first_data_id}, {last_data_id})")

## Scan the LF Durations
# params = default_params.copy()
# lf_durations = np.arange(0.001, 0.2, 0.01)
# lf_durations *= ureg.ms
# sequence = get_sequence(params)
# sequence.setup_sequence(use_opposite_field=False)
# m4i.setup_sequence(sequence)
# for kk in tqdm(range(len(lf_durations))):
#     params["lf"]["duration"] = lf_durations[kk]
#     del sequence._segments["lf"]
#     sequence._define_lf()
#     m4i.change_segment("lf")
#     m4i.setup_sequence_steps_only()
#     m4i.write_all_setup()
#     data = run_sequence(sequence, params, skip_setup=True)
#     data_id = save_data(sequence, params, *data)
#     if kk == 0:
#         first_data_id = data_id
#         print(first_data_id)
#     elif kk == len(lf_durations) - 1:
#         last_data_id = data_id
# print(f"({first_data_id}, {last_data_id})")

## Scan the LF Frequencies
# params = default_params.copy()
# lf_frequencies = np.arange(248, 258, 0.2)
# lf_frequencies *= ureg.kHz
# sequence = get_sequence(params)
# sequence.setup_sequence(use_opposite_field=False)
# m4i.setup_sequence(sequence)
# while True:
#     for kk in tqdm(range(len(lf_frequencies))):
#         for phase_diff in [0, np.pi]:
#             params["lf"]["center_frequency"] = lf_frequencies[kk]
#             params["lf"]["phase_diff"] = phase_diff
#             del sequence._segments["lf"]
#             sequence._define_lf()
#             m4i.change_segment("lf")
#             m4i.setup_sequence_steps_only()
#             m4i.write_all_setup()
#             data = run_sequence(sequence, params, skip_setup=True)
#             data_id = save_data(sequence, params, *data)
#             print(data_id)
#         if kk == 0:
#             first_data_id = data_id
#             print(first_data_id)
#         elif kk == len(lf_frequencies) - 1:
#             last_data_id = data_id
#     print(f"({first_data_id}, {last_data_id})")


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


## Scan the LF Detunings, bbar, time series (T-violation), faster awg, a-abar and b-bbar
# params = default_params.copy()
# lf_frequencies = np.array([-1, 1])
# lf_frequencies *= ureg.kHz
# lf_phases = np.array([np.pi / 2, -np.pi / 2])
#
# opposite_field_plates = [False, True]
# for kk in range(1000000):
#     for field_plate in [1,1.5,2,2.5,3]:
#         params["field_plate"]["amplitude"] = 4500 * field_plate
#         params["field_plate"]["stark_shift"] = 2 * ureg.MHz * field_plate
#         for jj in range(1, 2):
#             if jj == 0:
#                 params["lf"]["center_frequency"] = 250.7 * ureg.kHz
#                 params["lf"]["amplitude"] = 8000
#                 params["rf"]["center_detuning"] = 48 * ureg.kHz
#                 params["rf"]["pre_lf"] = True
#             else:
#                 params["lf"]["center_frequency"] = 139.4 * ureg.kHz
#                 params["lf"]["amplitude"] = 1500
#                 params["rf"]["center_detuning"] = -52 * ureg.kHz
#                 params["rf"]["pre_lf"] = False
#             sequence = get_sequence(params)
#             sequence.setup_sequence(use_opposite_field=False)
#             m4i.setup_sequence(sequence)
#
#             for ll in opposite_field_plates:
#                 sequence.setup_sequence(use_opposite_field=ll)
#                 for freq in lf_frequencies:
#                     params["lf"]["detuning"] = freq
#                     for phase in lf_phases:
#                         params["lf"]["phase_diff"] = phase
#                         del sequence._segments["lf"]
#                         sequence._define_lf()
#                         m4i.change_segment("lf")
#                         m4i.setup_sequence_steps_only()
#                         m4i.write_all_setup()
#                         def worker():
#                             start_time = time.time()
#                             data = run_sequence(sequence, params, skip_setup=True)
#                             return (start_time, data)
#                         start_time, data = run_expt_check_lock(worker)
#                         data_id = save_data(sequence, params, *data, extra_headers={"start_time": start_time})
#                         if freq == lf_frequencies[0] and phase == lf_phases[0]:
#                             first_data_id = data_id
#                         if freq == lf_frequencies[-1] and phase == lf_phases[-1]:
#                             last_data_id = data_id
#                 print(f"{jj}, {ll}, ({first_data_id}, {last_data_id}) for field plate {field_plate}")
    #

## Scan the LF Detunings, bbar, time series (T-violation), faster awg
# params = default_params.copy()
# lf_frequencies = np.array([-0.7, 0.7])
# lf_frequencies = np.linspace(-1, 1, 5)
# lf_frequencies *= ureg.kHz
# lf_phases = np.array([np.pi / 2, -np.pi / 2])
#
# sequence = get_sequence(params)
# sequence.setup_sequence(use_opposite_field=False)
# m4i.setup_sequence(sequence)
#
# opposite_field_plates = [False, True]
# for kk in range(1000000):
#     for ll in opposite_field_plates:
#         sequence.setup_sequence(use_opposite_field=ll)
#         for phase in lf_phases:
#             params["lf"]["phase_diff"] = phase
#             for freq in lf_frequencies:
#                 params["lf"]["detuning"] = freq
#                 del sequence._segments["lf"]
#                 sequence._define_lf()
#                 m4i.change_segment("lf")
#                 m4i.setup_sequence_steps_only()
#                 m4i.write_setup_only()
#                 data = run_sequence(sequence, params, skip_setup=True)
#                 data_id = save_data(sequence, params, *data)
#                 if freq == lf_frequencies[0]:
#                     first_data_id = data_id
#                 if freq == lf_frequencies[-1]:
#                     last_data_id = data_id
#             print(f"{ll}, {phase}, ({first_data_id}, {last_data_id})")

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