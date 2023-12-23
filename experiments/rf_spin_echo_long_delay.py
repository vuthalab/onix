import time

import numpy as np
from onix.data_tools import save_experiment_data
from onix.headers.awg.M4i6622 import M4i6622
from onix.headers.pcie_digitizer.pcie_digitizer import Digitizer
from onix.sequences.rf_spin_echo_long_delay import RFSpinEchoLongDelay
from onix.experiments.helpers import data_averaging
from onix.units import ureg

try:
    m4i
    print("m4i is already defined.")
except Exception:
    m4i = M4i6622()

try:
    dg
    print("dg is already defined.")
except Exception:
    dg = Digitizer()


## function to run the experiment
def run_experiment(params):
    sequence = RFSpinEchoLongDelay(  # Only change the part that changed
        ao_parameters=params["ao"],
        eos_parameters=params["eos"],
        field_plate_parameters=params["field_plate"],
        chasm_parameters=params["chasm"],
        antihole_parameters=params["antihole"],
        rf_parameters=params["rf"],
        detect_parameters=params["detect"],
    )
    sequence.setup_sequence()
    m4i.setup_sequence(sequence)

    transmissions = None
    dg.start_capture()
    time.sleep(0.1)

    for kk in range(params["repeats"]):
        print(f"{kk / params['repeats'] * 100:.0f}%")
        m4i.start_sequence()
        m4i.wait_for_sequence_complete()
    m4i.stop_sequence()

    dg.wait_for_data_ready()
    digitizer_sample_rate, digitizer_data = dg.get_data()
    transmissions = np.array(digitizer_data[0])
    monitors = np.array(digitizer_data[1])

    photodiode_times = [kk / digitizer_sample_rate for kk in range(len(transmissions[0]))]
    transmissions_avg, transmissions_err = data_averaging(transmissions, digitizer_sample_rate, sequence.analysis_parameters["detect_pulse_times"])
    monitors_avg, monitors_err = data_averaging(monitors, digitizer_sample_rate, sequence.analysis_parameters["detect_pulse_times"])

    #import matplotlib.pyplot as plt
    #plt.plot(photodiode_times, transmissions[0])
    #plt.show()

    data = {
        "transmissions_avg": transmissions_avg,
        "transmissions_err": transmissions_err,
        "monitors_avg": monitors_avg,
        "monitors_err": monitors_err,
    }
    headers = {
        "params": params,
        "detunings": sequence.analysis_parameters["detect_detunings"]
    }
    name = "RF Spin Echo"
    data_id = save_experiment_data(name, data, headers)
    print(data_id)
    print()


## parameters
default_params = {
    "wm_channel": 5,
    "repeats": 20,
    "ao": {
        "name": "ao_dp",
        "order": 2,
        "frequency": 74 * ureg.MHz,  # TODO: rename it to "center_frequency"
        "amplitude": 2000,
        "detect_amplitude": 650,
        "rise_delay": 1.1 * ureg.us,
        "fall_delay": 0.6 * ureg.us,
    },
    "eos": {
        "ac": {
            "name": "eo_ac",
            "amplitude": 4500,  #4500
            "offset": -300 * ureg.MHz,
        },
        "bb": {
            "name": "eo_bb",
            "amplitude": 1900,  #1900
            "offset": -300 * ureg.MHz,
        },
        "ca": {
            "name": "eo_ca",
            "amplitude": 1400,  #1400
            "offset": -300 * ureg.MHz,
        },
    },
    "field_plate": {
        "name": "field_plate",
        "use": False,
        "amplitude": 0,
        "stark_shift": 1 * ureg.MHz,
        "padding_time": 5 * ureg.ms,
    },
    "chasm": {
        "transition": "bb",
        "scan": 2.8 * ureg.MHz,
        "scan_rate": 5 * ureg.MHz / ureg.s,
        "detuning": 0 * ureg.MHz,
    },
    "antihole": {
        "transitions": ["ac", "ca"],
        "scan": 0 * ureg.MHz,
        "scan_rate": 0 * ureg.MHz / ureg.s,
        "detuning": 0 * ureg.MHz,
        "duration_no_scan": 0.5 * ureg.s,
        "rf_assist": {
            "use": False,
            "use_sequential": True,
            "name": "rf_coil",
            "transition": "ab",
            "offset_start": 30 * ureg.kHz, # -110 * ureg.kHz
            "offset_end": 170 * ureg.kHz, # 20 * ureg.kHz
            "amplitude": 4200,
            "duration": 5 * ureg.ms,
        }
    },
    "detect": {
        "transition": "bb",
        "trigger_channel": 2,
        "detunings": np.linspace(-2, 2, 20) * ureg.MHz,
        "randomize": True,
        "on_time": 10 * ureg.us,
        "off_time": 2 * ureg.us,
        "chasm_repeats": 100,  # change the names of detection repeats
        "antihole_repeats": 100,
        "rf_repeats": 100,
    },
    "rf": {
        "name": "rf_coil",
        "transition": "ab",
        "amplitude": 4200,  #4200
        "offset": -46 * ureg.kHz,
        "detuning": 0 * ureg.kHz,
        "piov2_time": 0.025 * ureg.ms,
        "pi_time": 0.09 * ureg.ms,
        "delay_time": 3 * ureg.ms,
        "phase": 0,
    },
}
default_sequence = RFSpinEchoLongDelay(
    ao_parameters=default_params["ao"],
    eos_parameters=default_params["eos"] ,
    field_plate_parameters=default_params["field_plate"],
    chasm_parameters=default_params["chasm"],
    antihole_parameters=default_params["antihole"],
    rf_parameters=default_params["rf"],
    detect_parameters=default_params["detect"],
)
default_sequence.setup_sequence()

digitizer_time_s = default_sequence.analysis_parameters["digitizer_duration"].to("s").magnitude
sample_rate = 1e8
dg.set_acquisition_config(
    num_channels=2,
    sample_rate=1e8,
    segment_size=int(digitizer_time_s * sample_rate),
    segment_count=default_sequence.num_of_records() * default_params["repeats"]
)
dg.set_channel_config(channel=1, range=2)
dg.set_channel_config(channel=2, range=0.5)
dg.set_trigger_source_edge()
dg.write_configs_to_device()


## scan
# rf_phase_diffs = np.linspace(0, 2 * np.pi, 15)
# rf_delays = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 15, 20, 25, 30, 40, 50, 60, 70, 80, 90, 100, 120, 140, 160]) * ureg.ms
# rf_offsets = np.array([-46, 250, 100, -203]) * ureg.kHz
# rf_assist_offset_starts = np.array([30, 30, -110, -110]) * ureg.kHz
# rf_assist_offset_ends = np.array([170, 170, 20, 20]) * ureg.kHz

rf_phase_diffs = np.linspace(0, 2 * np.pi, 5)
rf_delays = np.array([3]) * ureg.ms
rf_offsets = np.array([-46, 100]) * ureg.kHz
rf_assist_offset_starts = np.array([30, -110]) * ureg.kHz
rf_assist_offset_ends = np.array([170, 20]) * ureg.kHz

params = default_params.copy()
for kk in range(len(rf_offsets)):
    params["rf"]["offset"] = rf_offsets[kk]
    params["antihole"]["rf_assist"]["offset_start"] = rf_assist_offset_starts[kk]
    params["antihole"]["rf_assist"]["offset_end"] = rf_assist_offset_ends[kk]
    for ll in range(len(rf_delays)):
        params["rf"]["delay_time"] = rf_delays[ll]
        for mm in range(len(rf_phase_diffs)):
            params["rf"]["phase"] = rf_phase_diffs[kk]
            run_experiment(params)
# for kk in range(len(rf_offsets)):
#     params["rf"]["offset"] = rf_offsets[kk]
#     params["antihole"]["rf_assist"]["offset_start"] = rf_assist_offset_starts[kk]
#     params["antihole"]["rf_assist"]["offset_end"] = rf_assist_offset_ends[kk]
#     for ll in range(len(rf_delays)):
#         params["rf"]["delay_time"] = rf_delays[ll]
#         for mm in range(len(rf_phase_diffs)):
#             params["rf"]["phase"] = rf_phase_diffs[kk]
#             run_experiment(params)

## empty