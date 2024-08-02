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
from onix.headers.rigol_field_plate import Rigol
rigol = Rigol()
import os
import influxdb_client
from influxdb_client.client.write_api import SYNCHRONOUS
token = os.environ.get("INFLUXDB_TOKEN")
org = "onix"
url = "http://onix-pc:8086"
query_client = influxdb_client.InfluxDBClient(url=url, token=token, org=org)
def set_heater_output_power(self, channel, val):
    self._set_variable(f"{channel}.value", val)

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
cleanouts = 0
detects = 256
lf_counts = 7
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
        "detunings": np.array([0.0], dtype=float) * ureg.MHz,
        # "detunings": np.flip(np.linspace(-10, 10, 100)) * ureg.MHz,
        "on_time": 10 * ureg.us,  #40,
        "off_time": 2 * ureg.us,
        "delay": 8 * ureg.us,
        "ao_amplitude": 180, # 200,
        "simultaneous": False,
        "cycles": {},
        "fid": {
            "use": False,
            "pump_amplitude": 733,
            "pump_time": 45 * ureg.us,
            "probe_detuning": -10 * ureg.MHz,
            "probe_amplitude": 180,
            "probe_time": 30 * ureg.us,
            "wait_time": 5 * ureg.us,
            "phase": 0,
        }
    },
    "rf": {
        "amplitude": 3875,
        "T_0": 0.3 * ureg.ms,
        "T_e": 0.15 * ureg.ms,
        "T_ch": 21 * ureg.ms,
        "scan_range": 45 * ureg.kHz,
    },
    "lf": {
        "center_frequencies": [(140.7 + (jj * 0.2)) * ureg.kHz for jj in range(freq_counts) for kk in range(lf_counts)],
        "amplitudes": [1000 for kk in range(lf_counts * freq_counts)],
        "wait_times": [0.35 * ureg.ms for kk in range(lf_counts * freq_counts)],
        "durations": [0.05 * ureg.ms for kk in range(lf_counts * freq_counts)],
        "detunings": [0. * ureg.kHz for kk in range(lf_counts * freq_counts)],
        "phase_diffs": list(np.linspace(0, 2*np.pi, lf_counts)) * freq_counts,
    },
    "field_plate": {
        "method": "ttl",
        "relative_to_lf": "after", #"before"= during optical, "after"=during detect
        "amplitude": 4500,
        "stark_shift": 2.2 * ureg.MHz,
        "ramp_time": 3 * ureg.ms,
        "wait_time": None,
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
    "digitizer": {
        "sample_rate": 25e6,
        "ch1_range": 2,
        "ch2_range": 2,
    },
    "sequence": {
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
            #("cleanout", cleanouts),
            ("optical_cb", cb_pumps),

            ("optical_ac", ac_pumps),
            #("detect_4", detects),
            #("rf_abar_bbar", 1),
            #("detect_5", detects),
            ("rf_a_b", 1),
            #("rf_abar_bbar", 1),
            ("lf_0", 1),
            ("rf_a_b", 1),
            ("detect_6", detects),
            #("cleanout", cleanouts),
            ("optical_cb", cb_pumps),
        ]
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
    sample_rate=default_params["digitizer"]["sample_rate"],
)

## Repeat the sequence
default_field_plate_amplitude = default_params["field_plate"]["amplitude"]

def run_1_experiment(only_print_first_last=False, repeats=50):
    params = default_params.copy()
    sequence = get_sequence(params)
    sequence.setup_sequence()
    m4i.setup_sequence(sequence)
    lf_indices = list(range(lf_counts*freq_counts))
    for kk in range(repeats):
        for ll, e_field in enumerate(["_opposite", ""]):
            if ll == 0:
                params["field_plate"]["amplitude"] = -default_field_plate_amplitude
            else:
                params["field_plate"]["amplitude"] = default_field_plate_amplitude
            if params["field_plate"]["method"] == "ttl":
                if params["field_plate"]["relative_to_lf"] == "before":
                    on_time = 10e-6 + (ac_pumps + cb_pumps) * 1e-3 # ms  ((((time is constant set in sequence code!!!)))))
                elif params["field_plate"]["relative_to_lf"] == "after":
                    on_time = 10e-6 + sequence.field_plate_on_time.to("s").magnitude

                rigol.field_plate_output(
                    amplitude = 2.5 * params["field_plate"]["amplitude"] / 2**15,
                    ramp_time = params["field_plate"]["ramp_time"].to("s").magnitude,
                    on_time = on_time,
                    set_params = True,
                )

            for jj, lf_index in enumerate(lf_indices):

                # E FIELD DURING OPTICAL (TODO: automate this list)
                if params["field_plate"]["relative_to_lf"] == "before":
                    params["sequence"]["sequence"] = [
                        ("field_plate_trigger", 1),
                        #("break", int(params["field_plate"]["wait_time"]/(10 * ureg.us))),
                        ("break", int(params["field_plate"]["ramp_time"]/(10 * ureg.us))),
                        ("optical_cb", cb_pumps),
                        ("optical_ac", ac_pumps),
                        ("break", 11),
                        ("rf_abar_bbar", 1),
                        (f"lf_{lf_index}", 1),
                        ("rf_abar_bbar", 1),
                        (f"detect{e_field}_3", detects),
                        #("cleanout", cleanouts),

                        ("field_plate_trigger", 1),
                        #("break", int(params["field_plate"]["wait_time"]/(10 * ureg.us))),
                        ("break", int(params["field_plate"]["ramp_time"]/(10 * ureg.us))),
                        ("optical_cb", cb_pumps),
                        ("optical_ac", ac_pumps),
                        ("break", 11),
                        ("rf_a_b", 1),
                        (f"lf_{lf_index}", 1),
                        ("rf_a_b", 1),
                        (f"detect{e_field}_6", detects),
                        #("cleanout", cleanouts),
                    ]

                # E FIELD DURING DETECTS
                elif params["field_plate"]["relative_to_lf"] == "after":
                    params["sequence"]["sequence"] = [

                        ("optical_ac", ac_pumps),
                        ("rf_abar_bbar", 1),
                        (f"lf_{lf_index}", 1),
                        ("rf_abar_bbar", 1),
                        ("field_plate_trigger", 1),
                       # ("break", int(params["field_plate"]["wait_time"]/(10 * ureg.us))),
                        ("break", int(params["field_plate"]["ramp_time"]/(10 * ureg.us))),
                        (f"detect{e_field}_3", detects),
                        ("break", 11),
                        #("cleanout", cleanouts),
                        ("optical_cb", cb_pumps),


                        ("optical_ac", ac_pumps),
                        ("rf_a_b", 1),
                        (f"lf_{lf_index}", 1),
                        ("rf_a_b", 1),
                        ("field_plate_trigger", 1),
                        #("break", int(params["field_plate"]["wait_time"]/(10 * ureg.us))),
                        ("break", int(params["field_plate"]["ramp_time"]/(10 * ureg.us))),
                        (f"detect{e_field}_6", detects),
                        ("break", 11),
                        #("cleanout", cleanouts),
                        ("optical_cb", cb_pumps),
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
                #time.sleep(0.2)
                if jj == 0:
                    first_data_id = data_id
                elif jj == lf_counts - 1:
                    last_data_id = data_id
            if not only_print_first_last:
                print(f"({first_data_id}, {last_data_id})")
            elif kk == 0 or kk == repeats - 1:
                print(f"({first_data_id}, {last_data_id})")

## Scan pi / 2 pulse duration
carrier_frequencies = np.arange(140.7, 142.1, 0.2)
for freq in carrier_frequencies:
    default_params["lf"]["center_frequencies"] = [freq * ureg.kHz for jj in range(freq_counts) for kk in range(lf_counts)]
    run_1_experiment(repeats = 13)


## 2D RF amplitude and duration scan
# duration_list = np.linspace(, 23,4)
# amplitude_list = np.linspace(2500, 8000, 5)
#
# for amplitude in amplitude_list:
#     for duration in duration_list:
#         default_params["rf"]["T_ch"] = duration * ureg.ms
#         default_params["rf"]["amplitude"] = amplitude
#         print(f"Amplitude = {amplitude} \t Duration = {duration} ms")
#         run_1_experiment(repeats = 8)


## RAMP TIME SCANS FOR BEFORE AND AFTER LF
# default_params["field_plate"]["relative_to_lf"] = "before"
# wait_times = [0, 7, 17, 27, 97]
# print("before")
# for wait_time in wait_times:
#     print(wait_time)
#     default_params["field_plate"]["wait_time"] = wait_time * ureg.ms
#     run_1_experiment(True, repeats=300) # 1 repeat = ~ 1 minute
#
#
# default_params["field_plate"]["relative_to_lf"] = "after"
# wait_times = [0, 7, 17, 27, 97]
# print("after")
# for wait_time in wait_times:
#     print(wait_time)
#     default_params["field_plate"]["wait_time"] = wait_time * ureg.ms
#     run_1_experiment(True, repeats=300)


## REDOING THE OPTICAL DETUNINGS SCAN WITH FIXED ELECTRIC FIELD USING RIGOL
# for kk in np.linspace(-1, 1, 11):
#     default_params["detect"]["detunings"] = np.array([kk], dtype=float) * ureg.MHz
#     print(default_params["detect"]["detunings"])
#     run_1_experiment(True, repeats=250)

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
