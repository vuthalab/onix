import time

import numpy as np
from onix.sequences.lf_quick_state_prep_axion import LFQuickStatePrepAxion
from onix.units import ureg
from onix.experiments.shared import (
    m4i,
    dg,
    update_parameters_from_shared,
    setup_digitizer,
    run_sequence,
    save_data,
    get_4k_platform_temp,
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
    sequence = LFQuickStatePrepAxion(params)
    return sequence


## parameters
ac_pumps = 25
cb_pumps = 25
chasms = 40
cleanouts = 0
detects = 32
detect_detunings = np.linspace(-4,4,40)
np.random.shuffle(detect_detunings)
scan_count = 8

default_params = {
    "name": "Simple LF Spectroscopy Quick State Prep",
    "sequence_repeats_per_transfer": 1,
    "data_transfer_repeats": 1,
    "ao": {
        "center_frequency": 72 * ureg.MHz, #73.15 * ureg.MHz,
    },
    "optical": {
        "ao_amplitude": 2000,
    },
    "chasm": {
        "scan": 5 * ureg.MHz, # 5 MHz
        "durations": 5 * ureg.ms, # 10 ms
        "ao_amplitude": 2000,
    },
    "detect": {
        "transition": "ac",
        # "detunings": np.array([-6, -5, -4, -3, -2.5, -2, -1.7, -1.3, -1, -0.8, -0.6, -0.4, -0.2, 0, 0.2, 0.4, 0.6, 0.8, 1, 1.3, 1.7, 2, 2.5, 3, 4, 5, 6]) * ureg.MHz,
        "detunings": detect_detunings * ureg.MHz,
        "on_time": 100 * ureg.us,
        "off_time": 2 * ureg.us,
        "delay": 8 * ureg.us,
        "ao_amplitude": 200,
        "simultaneous": False,
        "cycles": {}
    },
    "rf": {
        "HSH": {
            "use": True,
            "amplitude": 3875,
            "T_0": 0.3 * ureg.ms,
            "T_e": 0.15 * ureg.ms,
            "T_ch": 15 * ureg.ms,
            "scan_range": 45 * ureg.kHz,
        },
        "detuning_ab": 55 * ureg.kHz,
        "detuning_abarbbar": -60 * ureg.kHz,
        "amplitude": 5000,
        "duration":15 * ureg.ms,
        "offset": 30 * ureg.kHz,
    },
    "lf": {
        "center_frequency": 141.146 * ureg.kHz,
        "detuning": 0 * ureg.kHz,
        "amplitude": 1000,
        "piov2_time": 50 * ureg.us,
        "wait_time": 350 * ureg.us,
        "phase_diffs": np.linspace(0, np.pi * 2, scan_count, endpoint=False)
    },
    "field_plate": {
        "method": "ttl",
        "relative_to_lf": "before",
        "amplitude": 2000,
        "stark_shift": 1 *ureg.MHz,
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
    "digitizer": {
        "sample_rate": 25e6,
        "ch1_range": 2,
        "ch2_range": 2,
    },
    "sequence": {
        "sequence": [
            ("chasm", chasms),
            #(f"detect{e_field}_1", detects),
            ("field_plate_trigger", 1),
            ("break", 300),
            ("optical_cb", cb_pumps),
            ("optical_ac", ac_pumps),
            ("break", 200),
            ("lfpiov2", 1),
            (f"detect_1", detects),  # switch
            ("rf_ab", 1),
            (f"lf_0", 1),
            ("rf_abarbbar", 1),
            (f"detect_2", detects),
        ]
    }
}
default_params = update_parameters_from_shared(default_params)
default_sequence = get_sequence(default_params)
default_sequence.setup_sequence()



## E Field Reversals


def run_1_experiment(only_print_first_last=False, repeats=50):
    default_field_plate_amplitude = default_params["field_plate"]["amplitude"]
    params = default_params.copy()
    sequence = get_sequence(params)
    sequence.setup_sequence()
    setup_digitizer(
        sequence.analysis_parameters["digitizer_duration"],
        sequence.num_of_record_cycles(),
        params["sequence_repeats_per_transfer"],
        ch1_range=params["digitizer"]["ch1_range"],
        ch2_range=params["digitizer"]["ch2_range"],
        sample_rate=params["digitizer"]["sample_rate"],
    )
    m4i.setup_sequence(sequence)
    lf_indices = list(range(scan_count))
    for kk in range(repeats):

        if params["field_plate"]["method"] == "ttl":
            if params["field_plate"]["relative_to_lf"] == "before":
                on_time = 10e-6 + (ac_pumps + cb_pumps) * 1e-3 # ms  ((((time is constant set in sequence code!!!)))))
            elif params["field_plate"]["relative_to_lf"] == "after":
                on_time = 10e-6 + sequence.field_plate_on_time.to("s").magnitude
            print(f"Field plate amplitude = {params['field_plate']['amplitude']}")
            rigol.field_plate_output(
                amplitude = 2.5 * params["field_plate"]["amplitude"] / 2**15,
                ramp_time = params["field_plate"]["ramp_time"].to("s").magnitude,
                on_time = on_time,
                set_params = True,
            )
        for jj, lf_index in enumerate(lf_indices):

            # E FIELD DURING OPTICAL (TODO: automate this list)
            if params["field_plate"]["relative_to_lf"] == "after":
                params["sequence"]["sequence"] = [
                    ("chasm", chasms),
                    #("field_plate_trigger", 1),
                    #("break", int((3 * ureg.ms) / (10 * ureg.us))),
                    #(f"detect{e_field}_1", detects),
                    # ("optical_cb", cb_pumps),
                    # ("optical_ac", ac_pumps),
                    # ("break", 200),
                    # ("lfpiov2", 1),


                    # ("field_plate_trigger", 1),
                    # ("break", int((3 * ureg.ms) / (10 * ureg.us))),
                    (f"detect{e_field}_1", detects),  # switch


                    # ("rf_abarbbar", 1),
                    # (f"lf_{lf_index}", 1),
                    # ("rf_abarbbar", 1),
                    #
                    #
                    # ("field_plate_trigger", 1),
                    # ("break", int((3 * ureg.ms) / (10 * ureg.us))),
                    # (f"detect{e_field}_2", detects),
                ]


            # E FIELD DURING DETECT (TODO: automate this list)
            if params["field_plate"]["relative_to_lf"] == "before":
                params["sequence"]["sequence"] = [
                    ("chasm", chasms),
                    #(f"detect{e_field}_1", detects),
                    ("field_plate_trigger", 1),
                    ("break", int(params["field_plate"]["ramp_time"]/(10 * ureg.us))),
                    ("optical_cb", cb_pumps),
                    ("optical_ac", ac_pumps),
                    ("break", 200),
                    ("lfpiov2", 1),
                    (f"detect_1", detects),  # switch
                    ("rf_abarbbar", 1),

                    # ("break", 10000),
                    (f"lf_{lf_index}", 1),
                    ("rf_abarbbar", 1),
                    # ("field_plate_trigger", 1),
                    # ("break", int(params["field_plate"]["ramp_time"]/(10 * ureg.us))),
                    (f"detect_2", detects),
                ]

            sequence.setup_sequence()
            m4i.setup_sequence_steps_only()
            m4i.write_all_setup()

            def worker():
                start_time = time.time()
                data = run_sequence(sequence, params, skip_setup=True)
                return (start_time, data)
            start_time, data = run_expt_check_lock(worker)
            try:
                temp = get_4k_platform_temp(time.time() - start_time)
            except:
                temp = None
            data_id = save_data(sequence, params, *data, extra_headers={"start_time": start_time, "temp": temp})
            time.sleep(1)
            print(data_id)
            if jj == 0:
                first_data_id = data_id
            elif jj == scan_count - 1:
                last_data_id = data_id
        if not only_print_first_last:
            print(f"({first_data_id}, {last_data_id})")
        elif kk == 0 or kk == repeats - 1:
            print(f"({first_data_id}, {last_data_id})")

###
E_magnitudes = [2000, -2000, 3000, -3000, 5000, - 5000]
stark_shifts = [i * (2.2 / 4500) for i in E_magnitudes]
detect_detunings = [
    np.array([-1.2,-1,-1.35,-.85,-1.55,-.65,-1.8,-.3, 0,-2.3,-3,.9, 1.05, 0.7, 1.25, 0.55,1.5, 0.35, 1.8, 3, 1.1, 0.45,-0.8, -1.45]),
    np.array([-1.2,-1,-1.35,-.85,-1.55,-.65,-1.8,-.3, 0,-2.3,-3,.9, 1.05, 0.7, 1.25, 0.55,1.5, 0.35, 1.8, 3, 1.1, 0.45,-0.8, -1.45]),
    np.array([-1.6, -1.4, -1.8, -1.2, -2, -1, -2.2, -2.5, -3.5, 0, 1.3, 1.5, 1.1, 1.7, 0.9, 1.9, 0.7, 0.3, 2.5, 3.5, -1.9, -1.45, 1, 1.6, -0.8, 4]),
    np.array([-1.6, -1.4, -1.8, -1.2, -2, -1, -2.2, -2.5, -3.5, 0, 1.3, 1.5, 1.1, 1.7, 0.9, 1.9, 0.7, 0.3, 2.5, 3.5, -1.9, -1.45, 1, 1.6, -0.8, 4]),
    np.array([-2.6, -2.4, -2.8, -2.2, -3, -2, -3.2,-3.7,-4.4, -1, 0, 2.1, 1.9, 2.3, 1.7, 2.5, 1.5,2.7, 3.5,4.4, 0.8, 2.8, -1.7,-2.9]),
    np.array([-2.6, -2.4, -2.8, -2.2, -3, -2, -3.2,-3.7,-4.4, -1, 0, 2.1, 1.9, 2.3, 1.7, 2.5, 1.5,2.7, 3.5,4.4, 0.8, 2.8, -1.7,-2.9])
    ]


for i in range(len(E_magnitudes)):
    s = time.time()
    default_params["detect"]["detunings"] = detect_detunings[i] * ureg.MHz
    default_params["field_plate"]["amplitude"] = E_magnitudes[i]
    default_params["field_plate"]["stark_shift"] = stark_shifts[i] * ureg.MHz
    run_1_experiment(repeats=int(360))
    print(time.time() - s)
