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
    get_4k_platform_temp
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
        #"detunings": np.flip(np.linspace(-10, 10, 30)) * ureg.MHz,
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
        "center_frequencies": [(141.146 + (jj * 0.2)) * ureg.kHz for jj in range(freq_counts) for kk in range(lf_counts)],
        "amplitudes": [1000 for kk in range(lf_counts * freq_counts)],
        "wait_times": [0.35 * ureg.ms for kk in range(lf_counts * freq_counts)],
        "durations": [0.05 * ureg.ms for kk in range(lf_counts * freq_counts)],
        "detunings": [0. * ureg.kHz for kk in range(lf_counts * freq_counts)],
        "phase_diffs": list(np.linspace(0, 2*np.pi, lf_counts)) * freq_counts,
    },
    "field_plate": {
        "method": "ttl",
        "relative_to_lf": "before", #"before"= during optical, "after"=during detect
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


##
amplitudes = np.linspace(1000, 7500, 6)
T0s = np.flip([0.01, 0.05, 0.1, 0.15])
Tes = np.flip([0.05, 0.1, 0.15, 0.2])
Tchs = np.flip(np.linspace(1, 26, 20))
for T0 in T0s:
    for Te in Tes:
        for Tch in Tchs:
            for amplitude in amplitudes:
                default_params["rf"]["amplitude"] = amplitude
                default_params["rf"]["T_0"] = T0 * ureg.ms
                default_params["rf"]["T_e"] = Te * ureg.ms
                default_params["rf"]["T_ch"] = Tch * ureg.ms
                start_time = time.time()
                run_1_experiment(repeats=5)
                print(time.time() - start_time)


