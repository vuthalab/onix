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
ac_pumps = 25 #250*2
cb_pumps = 25 #250*2
chasms = 10 #10#400*2
cleanouts = 0
detects = 512
scan_count = 8

# four total experiments: (chasm , no chasm) x (mirror_cb, no mirror_cb)
# chasms = 0, 40
# use_mirror_cb": False, True
# use ao_amplitude_cb = 1000 for all 4 experiments.

default_params = {
    "name": "Simple LF Spectroscopy Quick State Prep",
    "sequence_repeats_per_transfer": 1,
    "data_transfer_repeats": 1,
    "ao": {
        "center_frequency": 80 * ureg.MHz, #73.15 * ureg.MHz,
    },
    "optical": {
        "ao_amplitude_ac": 2000,
        "ao_amplitude_cb": 2000,
        "cb_detuning": -18 * ureg.MHz,
        "use_mirror_cb": False,
    },
    "chasm": {
        "scan": 8 * ureg.MHz, # 5 MHz
        "durations": 8 * ureg.ms, # 10 ms
        "ao_amplitude": 2000,
    },
    "detect": {
        "transition": "ac",
        "detunings": np.linspace(-3.5, 3.5, 35) * ureg.MHz,
        # "detunings": np.array([2.3]) * ureg.MHz,
        "on_time": 5 * ureg.us,
        "off_time": 1 * ureg.us,
        "delay": 8 * ureg.us,
        "ao_amplitude": 220,
        "simultaneous": False,
        "save_avg": True,
        "fid": {
            "use": False,
            "save_avg": True,
            "pump_amplitude": 733 * 2,
            "pump_time": 5 * ureg.us,
            "num_jumps": 40,
            "pump_scan": 0.2 * ureg.MHz,
            "probe_detuning": 10 * ureg.MHz,
            "probe_amplitude": 220,
            "probe_time": 15 * ureg.us,
            "wait_time": 1 * ureg.us,
            "phase": 0,
        }
    },
    "rf": {
        "HSH": {
            "use": True,
            "amplitude": 4000,
            "T_0": 0.3 * ureg.ms,
            "T_e": 0.15 * ureg.ms,
            "T_ch": 25 * ureg.ms,
            "scan_range": 60 * ureg.kHz,
        },
        "detuning_ab": 55 * ureg.kHz, # 53
        "detuning_abarbbar": -60 * ureg.kHz, # -57
        "amplitude": 5000,
        "duration": 15 * ureg.ms,
        "offset": 30 * ureg.kHz,
    },
    "lf": {
        "center_frequency": 141.2 * ureg.kHz,
        "detuning": 0 * ureg.kHz,
        "amplitude": 1000,
        "piov2_time": 50 * ureg.us,
        "wait_time": 350 * ureg.us,
        "phase_diffs": np.linspace(0, np.pi * 2, scan_count, endpoint=False)
    },
    "field_plate": {
        "method": "ttl",
        "relative_to_lf": "before",
        "amplitude": 4500*1.5,
        "stark_shift": 2.2*1.5* ureg.MHz, #2.2 *ureg.MHz,
        "ramp_time": 3 * ureg.ms,
        "wait_time": None,
        "use": True,
    },
    "digitizer": {
        "sample_rate": 25e6,
        "ch1_range": 2,
        "ch2_range": 2,
    },
    "sequence": {
        "sequence": [
            # ("field_plate_trigger", 1),
            # ("break", 300),
            ("optical_cb", cb_pumps),
            ("optical_ac", ac_pumps),
            ("break", 200),
            ("lfpiov2", 1),
            ("field_plate_trigger", 1),
            ("break", 300),
            (f"detect_1", detects),
            ("rf_ab", 1),
            (f"lf_0", 1),
            ("rf_abarbbar", 1),
            ("field_plate_trigger", 1),
            ("break", 300),
            (f"detect_2", detects),
        ]
    },
    "sleep": 0 * ureg.s,
}
default_params = update_parameters_from_shared(default_params)


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

    for kk in tqdm(range(repeats)):
        # for field in [4500, -4500]:
        #     params["field_plate"]["amplitude"] = field
        #     rigol.field_plate_output(
        #         amplitude = 2.5 * params["field_plate"]["amplitude"] / 2**15,
        #         ramp_time = params["field_plate"]["ramp_time"].to("s").magnitude,
        #         on_time = on_time,
        #         set_params = True,
        #     )
        for jj, lf_index in enumerate(lf_indices):
            params["sequence"]["sequence"] = [
                ("chasm", chasms),
                ("field_plate_trigger", 1),
                ("break", int(params["field_plate"]["ramp_time"]/(10 * ureg.us))),
                ("optical_cb", cb_pumps),
                ("optical_ac", ac_pumps),
                ("break", 200),

                #("field_plate_trigger", 1),
                #("break", int(params["field_plate"]["ramp_time"]/(10 * ureg.us))),
                (f"detect_1", detects),

                ("lfpiov2", 1),
                #("break", 11),
                ("rf_abarbbar", 1),
                (f"lf_{lf_index}", 1),
                ("rf_abarbbar", 1),

                #("field_plate_trigger", 1),
                #("break", int(params["field_plate"]["ramp_time"]/(10 * ureg.us))),
                (f"detect_2", detects),
                #("break", 11),
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

            time.sleep(params["sleep"].to('s').magnitude)

            if jj == 0:
                first_data_id = data_id
            elif jj == scan_count - 1:
                last_data_id = data_id

        if not only_print_first_last:
            print(f"({first_data_id}, {last_data_id})")
        elif kk == 0 or kk == repeats - 1:
            print(f"({first_data_id}, {last_data_id})")

run_1_experiment(only_print_first_last=False, repeats = 100000)


# pump_times = np.linsapce(1, 50, 10) * ureg.us
# pump_amplitudes = np.linspace(200, 1000, 10)
#
# for pump_time in pump_times:
#     for pump_amplitude in pump_amplitudes:
#         default_params["detect"]["fid"]["pump_time"] = pump_times
#         default_params["detect"]["fid"]["pump_amplitude"] = pump_amplitude
#         print(f"Detuning = {detuning} \t Amplitude = {amplitude}")
#         s = time.time()
#         run_1_experiment(repeats = 1, only_print_first_last = True)
#         print(f"Took {time.time() - s}")

###
#run_1_experiment(repeats = 10)

# 1 hour = 600 repeats without delay
###
# cb_detunings = np.array([-19, -18.5, -18, -17.5, -17])
# for cb_detuning in cb_detunings:
#     print("cb detuning: ", cb_detuning)
#     default_params["optical"]["cb_detuning"] = cb_detuning * ureg.MHz
#     run_1_experiment(True, 600)
