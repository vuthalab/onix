import time

import numpy as np
from onix.sequences.simple_lf_quick_state_prep import SimpleLFQuickStatePrep
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
query_api = query_client.query_api()


## function to run the experiment
def get_sequence(params):
    sequence = SimpleLFQuickStatePrep(params)
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
detects = 128

scan_count = 50

default_params = {
    "name": "Simple LF Spectroscopy Quick State Prep",
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
        "on_time": 10 * ureg.us,
        "off_time": 2 * ureg.us,
        "delay": 8 * ureg.us,
        "ao_amplitude": 180,
        "simultaneous": False,
        "cycles": {
            '1': detects,
            '2': detects,
        }
    },
    "rf": {
        "HSH": {
            "use": True,
            "amplitude": 10000,
            "T_0": 0.1 * ureg.ms,
            "T_e": 0.15 * ureg.ms,
            "T_ch": 5 * ureg.ms,
            "scan_range": 20 * ureg.kHz,
        },
        "amplitude": 10000,
        "duration": 0.15 * ureg.ms,
        "detuning_ab": 50 * ureg.kHz,
        "detuning_abarbbar": -60 * ureg.kHz,
        "offset": 30 * ureg.kHz,
    },
    "lf": {
        "center_frequency": 141.146 * ureg.kHz, #250. * ureg.kHz, #141.146 * ureg.kHz,

        "amplitudes": [10000 for kk in range(scan_count)],

        # FREQUENCY SCAN ( set scan count = 150 )
        # "durations": [2 * ureg.ms for kk in range(scan_count)],
        # "detunings": np.linspace(-8, 5, scan_count) * ureg.kHz,

        # TIME SCAN,
        "durations": np.linspace(0.001, 0.1, scan_count) * ureg.ms,
        "detunings": [0 * ureg.kHz for jj in range(scan_count)],

        "this_detuning": None,
        "this_duration": None,

    },
    "field_plate": {
        "method": "ttl",
        "relative_to_lf": "after", #"before"= during optical, "after"=during detect
        "amplitude": 4500,
        "stark_shift": 2.2 * ureg.MHz,
        "ramp_time": 3 * ureg.ms,
        "wait_time": None,
        "use": False,
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
            ("optical_cb", cb_pumps),
            ("optical_ac", ac_pumps),
            ("lfpiov2", 1),
            ("detect_1", detects),
            ("rf_abarbbar", 1),
            (f"lf_0", 1),
            ("rf_abarbbar", 1),
            ("detect_2", detects),
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
def run_1_experiment(only__first_last=False, repeats=50):
    params = default_params.copy()
    sequence = get_sequence(params)
    sequence.setup_sequence()
    m4i.setup_sequence(sequence)

    lf_indices = list(range(scan_count))
    # print("T0", params["rf"]["HSH"]["T_0"], "Te", params["rf"]["HSH"]["T_e"], "Tch", params["rf"]["HSH"]["T_ch"], "amplitude", params["rf"]["HSH"]["amplitude"])

    for kk in range(repeats):
        for jj, lf_index in enumerate(lf_indices):
            sequence.setup_sequence()
            m4i.setup_sequence_steps_only()
            m4i.write_all_setup()
            params["lf"]["this_detuning"] = params["lf"]["detunings"][jj]
            params["lf"]["this_duration"] = params["lf"]["durations"][jj]

            params["sequence"]["sequence"] = [
                ("optical_cb", cb_pumps),
                ("optical_ac", ac_pumps),
                ("lfpiov2", 1),
                ("detect_1", detects),
                ("rf_abarbbar", 1),
                (f"lf_{lf_index}", 1),
                ("rf_abarbbar", 1),
                ("detect_2", detects),
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
            if only__first_last:
                print(data_id)
            time.sleep(0.2)
            if kk == 0 and jj == 0:
                start_id = data_id
            if kk == repeats-1 and jj == len(lf_indices)-1:
                print(start_id, ",", data_id)

run_1_experiment(repeats=30, only__first_last=True)

## HSH Scan
# amplitudes = [1000, 2500, 5000, 7500]
# T0s = np.flip([0.01, 0.05, 0.1, 0.15])
# Tes = np.flip([0.05, 0.1, 0.15, 0.2])
# Tchs = np.flip([0.75, 1, 2, 3, 4, 5, 6, 7, 8, 8.5, 9, 9.5, 10])
# for T0 in T0s:
#     for Te in Tes:
#         for Tch in Tchs:
#             for amplitude in amplitudes:
#                 default_params["rf"]["HSH"]["amplitude"] = amplitude
#                 default_params["rf"]["HSH"]["T_0"] = T0 * ureg.ms
#                 default_params["rf"]["HSH"]["T_e"] = Te * ureg.ms
#                 default_params["rf"]["HSH"]["T_ch"] = Tch * ureg.ms
#                 start_time = time.time()
#                 run_1_experiment(repeats=5)
#                 print(time.time() - start_time)