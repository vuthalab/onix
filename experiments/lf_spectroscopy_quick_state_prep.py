import time

import numpy as np
from onix.sequences.lf_spectroscopy_quick_state_prep import LFSpectroscopyQuickStatePrep
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
import os
import influxdb_client
from influxdb_client.client.write_api import SYNCHRONOUS
token = os.environ.get("INFLUXDB_TOKEN")
org = "onix"
url = "http://onix-pc:8086"
query_client = influxdb_client.InfluxDBClient(url=url, token=token, org=org)
query_api = query_client.query_api()


## function to run the experiment
def get_sequence(params):
    sequence = LFSpectroscopyQuickStatePrep(params)
    return sequence

## function to get 4K plate temp
def get_4k_platform_temp(average_time = 60):
    if average_time > 10:
        tables = query_api.query(
                (
                    f'from(bucket:"live") |> range(start: -{average_time}s) '
                    '|> filter(fn: (r) => r["_measurement"] == "temperatures")'
                    '|> filter(fn: (r) => r["_field"] == " 4k platform")'
                )
                )
        values =  np.array([record["_value"] for table in tables for record in table.records])
        return np.average(values)
    else:
        tables = query_api.query(
                (
                    f'from(bucket:"live") |> range(start: -20s) '
                    '|> filter(fn: (r) => r["_measurement"] == "temperatures")'
                    '|> filter(fn: (r) => r["_field"] == " 4k platform")'
                )
                )
        values =  np.array([record["_value"] for table in tables for record in table.records])
        return values[-1]



## parameters
ac_pumps = 25
cb_pumps = 25
cleanouts = 25
detects = 256
lf_counts = 9
freq_counts = 1

default_params = {
    "name": "LF Spectroscopy Quick State Prep",
    "sequence_repeats_per_transfer": 1,
    "data_transfer_repeats": 1,
    "ao": {
        "center_frequency": 75 * ureg.MHz,
    },
    "optical": {
        "ao_amplitude": 2000,
    },
    "detect": {
        "transition": "ac",
        "detunings": np.array([0]) * ureg.MHz,
        "on_time": 10 * ureg.us,
        "off_time": 2 * ureg.us,
        "delay": 8 * ureg.us,
        "ao_amplitude": 180,
        "simultaneous": False,
        "cycles": {},
    },
    "rf": {
        "amplitude": 8000,
        "T_0": 0.3 * ureg.ms,
        "T_e": 0.15 * ureg.ms,
        "T_ch": 10 * ureg.ms,
        "scan_range": 45 * ureg.kHz,
    },
    "lf": {
        "center_frequencies": [(141.146 + (jj * 0.1 )) * ureg.kHz for jj in range(freq_counts) for kk in range(lf_counts)],
        "amplitudes": [1000 for kk in range(lf_counts * freq_counts)],
        "wait_times": [0.35 * ureg.ms for kk in range(lf_counts * freq_counts)],
        "durations": [0.05 * ureg.ms for kk in range(lf_counts * freq_counts)],
        "detunings": [0. * ureg.kHz for kk in range(lf_counts * freq_counts)],
        "phase_diffs": list(np.linspace(0,2*np.pi, lf_counts))*freq_counts,
    },
    "field_plate": {
        "amplitude": 4500,
        "stark_shift": 2.2 * ureg.MHz,
        "use": True,
        "during": {
            "chasm": False,
            "antihole": False,
            "rf": False,
            "lf": False,
            "detect": True,
        }
    },
    "cleanout": {
        "amplitude": 0,
        "duration": 0.001 * ureg.us,
    },
    "sequence": {
        # "sequence": [
        #     ("optical_ac", ac_pumps),
        #     ("detect_1", detects),
        #     ("rf_a_b", 1),
        #     ("detect_2", detects),
        #     ("lf_0", 1),
        #     ("rf_a_b", 1),
        #     ("detect_3", detects),
        #     ("optical_cb", cb_pumps),
        #
        #     ("optical_ac", ac_pumps),
        #     ("detect_4", detects),
        #     ("rf_abar_bbar", 1),
        #     ("detect_5", detects),
        #     ("lf_0", 1),
        #     ("rf_abar_bbar", 1),
        #     ("detect_6", detects),
        #     ("optical_cb", cb_pumps),
        # ]
        "sequence": [
            ("optical_ac", ac_pumps),
            #("detect_1", detects),
            #("rf_a_b", 1),
            #("detect_2", detects),
            ("rf_abar_bbar", 1),
            #("rf_a_b", 1),
            ("lf_0", 1),
            ("rf_abar_bbar", 1),
            ("detect_3", detects),
            ("optical_cb", cb_pumps),
            #("cleanout", cleanouts),

            ("optical_ac", ac_pumps),
            #("detect_4", detects),
            #("rf_abar_bbar", 1),
            #("detect_5", detects),
            ("rf_a_b", 1),
            #("rf_abar_bbar", 1),
            ("lf_0", 1),
            ("rf_a_b", 1),
            ("detect_6", detects),
            ("optical_cb", cb_pumps),
            #("cleanout", cleanouts),
        ]
    }
}
default_params = update_parameters_from_shared(default_params)
# default_params["sequence"]["sequence"] = []
# field_plate = ""
# for ll, lf_index in enumerate([0, 1, 2, 3, 4, 5, 6, 7]):
#     detect_index_group = ll
#     default_params["sequence"]["sequence"].extend(
#         [
#             ("optical_ac", ac_pumps),
#             (f"detect{field_plate}_{detect_index_group * 6 + 1}", detects),
#             ("rf_a_b", 1),
#             (f"detect{field_plate}_{detect_index_group * 6 + 2}", detects),
#             (f"lf_{lf_index}", 1),
#             ("rf_a_b", 1),
#             (f"detect{field_plate}_{detect_index_group * 6 + 3}", detects),
#             ("optical_cb", cb_pumps),
#
#             ("optical_ac", ac_pumps),
#             (f"detect{field_plate}_{detect_index_group * 6 + 4}", detects),
#             ("rf_abar_bbar", 1),
#             (f"detect{field_plate}_{detect_index_group * 6 + 5}", detects),
#             (f"lf_{lf_index}", 1),
#             ("rf_abar_bbar", 1),
#             (f"detect{field_plate}_{detect_index_group * 6 + 6}", detects),
#             ("optical_cb", cb_pumps),
#         ]
#     )
# )
default_sequence = get_sequence(default_params)
default_sequence.setup_sequence()
setup_digitizer(
    default_sequence.analysis_parameters["digitizer_duration"],
    default_sequence.num_of_record_cycles(),
    default_params["sequence_repeats_per_transfer"],
    ch1_range=default_params["digitizer"]["ch1_range"],
    ch2_range=default_params["digitizer"]["ch2_range"],
)

## Repeat the sequence
default_field_plate_amplitude = default_params["field_plate"]["amplitude"]

def run_1_experiment():
    params = default_params.copy()
    params["detect"]["detunings"] = default_detect_detuning
    sequence = get_sequence(params)
    sequence.setup_sequence()
    m4i.setup_sequence(sequence)
    repeats = 300
    lf_indices = list(range(lf_counts*freq_counts))
    for kk in range(repeats):
        for ll, e_field in enumerate(["_opposite", ""]):
            if ll == 0:
                params["field_plate"]["amplitude"] = -default_field_plate_amplitude
            else:
                params["field_plate"]["amplitude"] = default_field_plate_amplitude
            for jj, lf_index in enumerate(lf_indices):
                params["sequence"]["sequence"] = [
                    ("optical_ac", ac_pumps),
                    ("rf_abar_bbar", 1),
                    (f"lf_{lf_index}", 1),
                    ("rf_abar_bbar", 1),
                    (f"detect{e_field}_3", detects),
                    ("optical_cb", cb_pumps),
                    #("cleanout", cleanouts),

                    ("optical_ac", ac_pumps),
                    ("rf_a_b", 1),
                    (f"lf_{lf_index}", 1),
                    ("rf_a_b", 1),
                    (f"detect{e_field}_6", detects),
                    ("optical_cb", cb_pumps),
                    #("cleanout", cleanouts),
                ]
                sequence.setup_sequence()
                m4i.setup_sequence_steps_only()
                m4i.write_all_setup()

                def worker():
                    start_time = time.time()
                    data = run_sequence(sequence, params, skip_setup=True)
                    return (start_time, data)
                start_time, data = run_expt_check_lock(worker)
                end_time = time.time()
                try:
                    temp = get_4k_platform_temp(end_time - start_time)
                except:
                    temp = None
                data_id = save_data(sequence, params, *data, extra_headers={"start_time": start_time, "temp": temp})
                time.sleep(0.2)
                if jj == 0:
                    first_data_id = data_id
                elif jj == lf_counts - 1:
                    last_data_id = data_id
            if kk == 0 or kk == repeats - 1:
                print(f"({first_data_id}, {last_data_id})")

detect_detunings = np.linspace(-1, 1, 11)
for detect_detuning in detect_detunings:
    print(detect_detuning)
    default_detect_detuning = np.array([detect_detuning]) * ureg.MHz
    run_1_experiment()

default_default_field_plate_amplitude = default_field_plate_amplitude
electric_field_multipliers = np.linspace(0.7, 1.3, 7)
for xx in electric_field_multipliers:
    print(xx)
    default_field_plate_amplitude = xx*default_default_field_plate_amplitude
    run_1_experiment()



## Scan the LF Detunings
# params = default_params.copy()
# lf_frequencies = np.arange(-25, 25, 1)
# lf_frequencies *= ureg.kHz
# sequence = get_sequence(params)
# sequence.setup_sequence()
# m4i.setup_sequence(sequence)
# for kk in tqdm(range(len(lf_frequencies))):
#     params["lf"]["detunings"] = [lf_frequencies[kk]]
#     del sequence._segments["lf_0"]
#     sequence._define_lf()
#     m4i.change_segment("lf_0")
#     m4i.setup_sequence_steps_only()
#     m4i.write_all_setup()
#     def worker():
#         start_time = time.time()
#         data = run_sequence(sequence, params, skip_setup=True)
#         return (start_time, data)
#     start_time, data = run_expt_check_lock(worker)
#     data_id = save_data(sequence, params, *data)
#     time.sleep(1)
#     if kk == 0:
#         first_data_id = data_id
#         print(first_data_id)
#     elif kk == len(lf_frequencies) - 1:
#         last_data_id = data_id
# print(f"({first_data_id}, {last_data_id})")

## Scan the LF Durations
# params = default_params.copy()
# lf_durations = np.arange(0.001, 0.1, 0.003)
# lf_durations *= ureg.ms
# sequence = get_sequence(params)
# sequence.setup_sequence()
# m4i.setup_sequence(sequence)
# for kk in tqdm(range(len(lf_durations))):
#     params["lf"]["durations"] = [lf_durations[kk]]
#     del sequence._segments["lf_0"]
#     sequence._define_lf()
#     m4i.change_segment("lf_0")
#     m4i.setup_sequence_steps_only()
#     m4i.write_all_setup()
#     def worker():
#         start_time = time.time()
#         data = run_sequence(sequence, params, skip_setup=True)
#         return (start_time, data)
#     start_time, data = run_expt_check_lock(worker)
#     data_id = save_data(sequence, params, *data)
#     time.sleep(1)
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
# default_fp_amplitude = default_params["field_plate"]["amplitude"]
#
# for jj in range(100000):
#     params = default_params.copy()
#     phases = np.linspace(0, 2 * np.pi, 9)
#     for ll in [-1, 1]:
#         params["field_plate"]["amplitude"] = default_fp_amplitude * ll
#         sequence = get_sequence(params)
#         sequence.setup_sequence()
#         m4i.setup_sequence(sequence)
#         for kk in range(len(phases)):
#             params["lf"]["phase_diffs"] = [phases[kk]]
#             del sequence._segments["lf_0"]
#             sequence._define_lf()
#             m4i.change_segment("lf_0")
#             m4i.setup_sequence_steps_only()
#             m4i.write_all_setup()
#             def worker():
#                 start_time = time.time()
#                 data = run_sequence(sequence, params, skip_setup=True)
#                 return (start_time, data)
#             start_time, data = run_expt_check_lock(worker)
#             data_id = save_data(sequence, params, *data)
#             if kk == 0:
#                 first_data_id = data_id
#             elif kk == len(phases) - 1:
#                 last_data_id = data_id
#     print(f"({first_data_id}, {last_data_id})")

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
# lf_frequencies = np.array([-2, 2])
# lf_frequencies *= ureg.kHz
# lf_phases = np.array([0])
# amplitude = default_params["field_plate"]["amplitude"]
# stark_shift = default_params["field_plate"]["stark_shift"]
#
# electric_polarity = [True, False]
# for kk in range(1000000):
#     for jj in range(0, 2):
#         if jj == 0:
#             params["lf"]["center_frequency"] = 251.0 * ureg.kHz
#             params["lf"]["duration"] = 0.06 * ureg.ms
#             params["lf"]["amplitude"] = 8000
#             params["rf"]["center_detuning"] = 48 * ureg.kHz
#             params["rf"]["pre_lf"] = True
#         else:
#             params["lf"]["center_frequency"] = 139.7 * ureg.kHz
#             params["lf"]["duration"] = 0.06 * ureg.ms
#             params["lf"]["amplitude"] = 625
#             params["rf"]["center_detuning"] = -52 * ureg.kHz
#             params["rf"]["pre_lf"] = False
#
#         ratios = [0.5, 0.75, 1, 1.5, 2, 2.5, 3]
#         np.random.shuffle(ratios)
#         for ratio in ratios:
#             for ll in electric_polarity:
#                 if ll:
#                     params["field_plate"]["amplitude"] = amplitude * ratio
#                     params["field_plate"]["stark_shift"] = stark_shift * ratio
#                 else:
#                     params["field_plate"]["amplitude"] = -amplitude * ratio
#                     params["field_plate"]["stark_shift"] = stark_shift * ratio
#                 sequence = get_sequence(params)
#                 sequence.setup_sequence(use_opposite_field=ll)
#                 m4i.setup_sequence(sequence)
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
#                         #time.sleep(10)
#                 print(f"{jj}, {ll}, ({first_data_id}, {last_data_id})")
#     #

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

## OPTIMIZE
# params = default_params.copy()
# optimizer = OptimizeExperiment(params)
# # optimizer.set_var_param(["chasm", "repeats"], (1, 50))
# # optimizer.set_var_param(["chasm", "durations"], (1, 15))
# # optimizer.set_var_param(["chasm", "ao_amplitude"], (500, 2500))
# # optimizer.set_var_param(["antihole", "repeats"], (1, 200))
# optimizer.set_var_param(["antihole", "durations"], (0.1, 10))
# optimizer.set_var_param(["antihole", "ao_amplitude_1"], (100, 2500))
# # optimizer.set_var_param(["antihole", "ao_amplitude_2"], (100, 2500))
# # optimizer.set_var_param(["rf_pump", "amplitude"], (100, 3000))
# result = optimizer.run_optimizer()

## OPTIMIZE TEST PARAMETERS
# params = default_params.copy()
# sequence = get_sequence(params)
# # params["chasm"]["repeats"] = 30
# # params["chasm"]["durations"] = 10.02 * ureg.ms
# # params["chasm"]["ao_amplitude"] = 851
# # params["antihole"]["repeats"] = 100
# # params["antihole"]["durations"] = 24.09 * ureg.ms
# # params["antihole"]["ao_amplitude_1"] = 2099
# # params["antihole"]["ao_amplitude_2"] = 112
# # params["rf_pump"]["amplitude"] = 1500
#
# params["lf"]["phase_diff"] = 0
# data = run_sequence(sequence, params)
# data_id_1 = save_data(sequence, params, *data)
#
# params["lf"]["phase_diff"] = np.pi
# data = run_sequence(sequence, params)
# data_id_2 = save_data(sequence, params, *data)
