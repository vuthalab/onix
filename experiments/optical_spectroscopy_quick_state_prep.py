import time

import numpy as np
from onix.sequences.optical_spectroscopy_quick_state_prep import OpticalSpectroscopyQuickStatePrep
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
    sequence = OpticalSpectroscopyQuickStatePrep(params)
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

detects = 128

detuning_counts = 1
duration_counts = 10

default_params = {
    "name": "Optical Spectroscopy Quick State Prep",
    "sequence_repeats_per_transfer": 1,
    "data_transfer_repeats": 1,
    "ao": {
        "center_frequency": 75 * ureg.MHz,
    },
    "optical": {
        "ao_amplitude": 2000,
        "amplitudes": [2000 for kk in range(detuning_counts * duration_counts)],
        "durations": [(kk + 1) * 5 * ureg.us for jj in range(detuning_counts) for kk in range(duration_counts)],
        "detunings": [0 * ureg.kHz for jj in range(detuning_counts) for kk in range(duration_counts)],
    },
    "detect": {
        "transition": "ac",
        "detunings": np.array([0.0], dtype=float) * ureg.MHz,
        "on_time": 40 * ureg.us,
        "off_time": 2 * ureg.us,
        "delay": 8 * ureg.us,
        "ao_amplitude": 200,
        "simultaneous": False,
        "cycles": {}
    },
    "rf": {
        "amplitude": 8000,
        "T_0": 0.3 * ureg.ms,
        "T_e": 0.15 * ureg.ms,
        "T_ch": 10 * ureg.ms,
        "scan_range": 45 * ureg.kHz,
    },
    "lf": {
        "amplitude": 1000,
        "duration": 0.05 * ureg.ms,
        "center_frequency": 141.5 * ureg.kHz,
        "detuning": 0 * ureg.kHz,
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
            ("lf", 1),
            ("rf_a_b", 1),
            ("rf_abar_bbar", 1),
            ("detect_1", detects),
            ("optical_0", 1),
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
default_field_plate_amplitude = default_params["field_plate"]["amplitude"]

def run_1_experiment(only_print_first_last=False, repeats=50):
    params = default_params.copy()
    sequence = get_sequence(params)
    sequence.setup_sequence()
    m4i.setup_sequence(sequence)

    optical_indices = list(range(detuning_counts * duration_counts))

    for kk in range(repeats):
        for jj, index in enumerate(optical_indices):
            sequence.setup_sequence()
            m4i.setup_sequence_steps_only()
            m4i.write_all_setup()
            params["optical"]["this_detuning"] = params["optical"]["detunings"][jj]
            params["optical"]["this_duration"] = params["optical"]["durations"][jj]

            params["sequence"]["sequence"] = [
                ("optical_cb", cb_pumps),
                ("optical_ac", ac_pumps),
                ("lf", 1),
                ("detect_1", detects),
                (f"optical_{index}", 1),
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
            time.sleep(0.2)

            if jj == 0:
                first_data_id = data_id
            elif jj == detuning_counts*duration_counts - 1:
                last_data_id = data_id
        if not only_print_first_last:
            print(f"({first_data_id}, {last_data_id})")
        elif kk == 0 or kk == repeats - 1:
            print(f"({first_data_id}, {last_data_id})")

while True:
    run_1_experiment()