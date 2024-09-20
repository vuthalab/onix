import time

import numpy as np

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

from onix.headers.rigol_dp832 import DP832
coil_supply = DP832()


## function to run the experiment
def get_sequence(params):
    sequence = LFQuickStatePrepAxion(params)
    return sequence


## parameters
ac_pumps = 25
cb_pumps = 25
chasms = 10
cleanouts = 0
detects = 128
scan_count = 8

default_params = {
    "name": "LF Spectroscopy",
    "sequence_repeats_per_transfer": 1,
    "data_transfer_repeats": 1,
    "ao": {
        "center_frequency": 80 * ureg.MHz,
    },
    "optical": {
        "ao_amplitude_ac": 2000,
        "ao_amplitude_cb": 2000,
        "cb_detuning": -18 * ureg.MHz,
        "duration": 8 * ureg.ms,
    },
    "chasm": {
        "scan": 8 * ureg.MHz,
        "duration": 8 * ureg.ms,
        "ao_amplitude": 2000,
    },
    "detect": {
        "method": "doa",  # "doa", "fid",
        "doa": {
            "transition": "ac",
            "detunings": np.linspace(-3.5, 3.5, 35) * ureg.MHz,
            "on_time": 5 * ureg.us,
            "off_time": 1 * ureg.us,
            "delay": 8 * ureg.us,
            "ao_amplitude": 180,
            "save_avg": True,
        },
        "fid": {
            "transition": "ac",
            "pump_amplitude": 1500,
            "pump_time": 5 * ureg.us,
            "pump_scan": 0.2 * ureg.MHz,
            "num_jumps": 40,
            "probe_amplitude": 120,
            "probe_time": 15 * ureg.us,
            "probe_detuning": 10 * ureg.MHz,
            "wait_time": 1 * ureg.us,
            "phase": 0,
            "save_avg": True,
        }
    },
    "rf": {
        "method": "hsh",  # "hsh", "sweep",
        "offset": 30 * ureg.kHz,
        "detuning_ab": 55 * ureg.kHz,
        "detuning_abarbbar": -60 * ureg.kHz,
        "hsh": {
            "amplitude": 4000,
            "T_0": 0.3 * ureg.ms,
            "T_e": 0.15 * ureg.ms,
            "T_ch": 25 * ureg.ms,
            "half_sweep_range": 30 * ureg.kHz,
        },
        "sweep": {
            "amplitude": 5000,
            "duration": 15 * ureg.ms,
            "half_sweep_range": 30 * ureg.kHz,
        }
    },
    "lf": {
        "method": "ramsey",  # "ramsey", "rabi",
        "center_frequency": 140.05 * ureg.kHz,  # change this iff the actual b-bbar center changes.
        "b_axis_Zeeman_shift": 2.3 * ureg.kHz,  # change this iff the B field along b changes.
        # carrier_frequency = center_frequency + b_axis_Zeeman_shift * Sigma + detuning.
        "ramsey": {
            "Sigma": 1,  # +1, 0, -1.
            "detuning": 0 * ureg.kHz,
            "amplitude": 250,
            "piov2_time": 200 * ureg.us,
            "wait_time": 300 * ureg.us,
            "phase_diffs": np.linspace(0, 2 * np.pi, scan_count, endpoint=False),
        },
        "rabi": {
            "Sigma": 0,  # +1, 0, -1.
            "detuning": 0 * ureg.kHz,
            "amplitude": 250,
            "pulse_time": 200 * ureg.us,
        }
    },
    "field_plate": {
        "method": "rigol",  # "awg", "rigol"
        "during": "detect", # "prep", "detect"
        "relative_to_lf": "before",
        "amplitude": 2 * ureg.V,
        "optical_shift_slope": 2 * ureg.MHz / ureg.V,
        "Pi": 1,  # +1, 0, -1.
        # V_output = amplitude * Pi
        # electric field induced optical frequency shift = V_output * optical_shift_slope
        "rigol": {
            "trigger_time": 10 * ureg.us,
            "ramp_up_time": 3 * ureg.ms,
            "ramp_down_time": 3 * ureg.ms,
        },
    },
    "digitizer": {
        "sample_rate": 25e6,
        "ch1_range": 2,
        "ch2_range": 2,
    },
    "sequence": {
        "steps": [
            ("optical_cb", cb_pumps),
            ("optical_ac", ac_pumps),
            ("break", 200),
            ("lfpiov2", 1),
            ("field_plate_trigger", 1),
            ("break", 300),
            ("detect_1", detects),
            ("rf_abarbbar", 1),
            ("lf_0", 1),
            ("rf_abarbbar", 1),
            ("field_plate_trigger", 1),
            ("break", 300),
            ("detect_2", detects),
        ]
    },
    "sleep": 0 * ureg.s,
}
default_params = update_parameters_from_shared(default_params)


## E Field Reversals
def run_1_experiment(only_print_first_last=False, repeats=50):
    print("switch")
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

    # coil_currents = [0, 2, 4, 6, 0]
    # for coil_current in coil_currents:
    #     params["coil"]["current"] = coil_current
    #     print(f"{coil_current} A")
    #     coil_supply.set_current(1, coil_current / 2)
    #     coil_supply.set_current(2, coil_current / 2)
    freq_list = np.array([137.8, 142.3])
    for kk in tqdm(range(repeats)):
        for ll in freq_list:
            params = default_params.copy()
            params["lf"]["center_frequency"] = ll * ureg.kHz
            sequence = get_sequence(params)
            sequence.setup_sequence()
            m4i.setup_sequence(sequence)
            for jj, lf_index in enumerate(lf_indices):
                params["sequence"]["sequence"] = [
                    ("chasm", chasms),
                    ("field_plate_trigger", 1),
                    ("break", int(params["field_plate"]["ramp_time"]/(10 * ureg.us))),
                    ("optical_cb", cb_pumps),
                    ("optical_ac", ac_pumps),
                    ("break", 200),
                    (f"detect_1", detects),

                    ("lfpiov2", 1),
                    ("rf_abarbbar", 1),
                    (f"lf_{lf_index}", 1),
                    ("rf_abarbbar", 1),
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
                time.sleep(params["sleep"].to('s').magnitude)

                if jj == 0:
                    first_data_id = data_id
                elif jj == scan_count - 1:
                    last_data_id = data_id
            try:
                if not only_print_first_last:
                    print(f"({first_data_id}, {last_data_id})")
                elif kk == 0 or kk == repeats - 1:
                    print(f"({first_data_id}, {last_data_id})")
            except:
                print(f"{first_data_id}")

run_1_experiment(only_print_first_last=False, repeats = 1)

###
#run_1_experiment(repeats = 10)

# 1 hour = 600 repeats without delay
###
# cb_detunings = np.array([-19, -18.5, -18, -17.5, -17])
# for cb_detuning in cb_detunings:
#     print("cb detuning: ", cb_detuning)
#     default_params["optical"]["cb_detuning"] = cb_detuning * ureg.MHz
#     run_1_experiment(True, 600)
