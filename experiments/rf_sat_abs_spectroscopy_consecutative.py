import time

import numpy as np
from onix.data_tools import save_experiment_data
from onix.headers.awg.M4i6622 import M4i6622
from onix.headers.pcie_digitizer.pcie_digitizer import Digitizer
from onix.sequences.rf_sat_abs_spectroscopy_consecutative import RFSatAbsSpectroscopyConsecutative
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
    sequence = RFSatAbsSpectroscopyConsecutative(  # Only change the part that changed
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
        #print(f"{kk / params['repeats'] * 100:.0f}%")
        m4i.start_sequence()
        m4i.wait_for_sequence_complete()
    m4i.stop_sequence()

    timeout = 1
    dg.wait_for_data_ready(timeout)
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
    name = "RF Saturation Absorption Spectroscopy Consecutative"
    data_id = save_experiment_data(name, data, headers)
    print(data_id)


## parameters
scan_range = 25
scan_step = 5
default_params = {
    "wm_channel": 5,
    "repeats": 5,
    "ao": {
        "name": "ao_dp",
        "order": 2,
        "frequency": 75 * ureg.MHz,  # TODO: rename it to "center_frequency"
        "amplitude": 2000,
        "detect_amplitude": 450,
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
        "use": True,
        "amplitude": 4500,
        "stark_shift": 2 * ureg.MHz,
        "padding_time": 5 * ureg.ms,
    },
    "chasm": {
        "transition": "bb",
        "scan": 3 * ureg.MHz,
        "scan_rate": 15 * ureg.MHz / ureg.s,
        "detuning": 0 * ureg.MHz,
    },
    "antihole": {
        "transitions": ["ac", "ca"],
        "scan": 0 * ureg.MHz,
        "scan_rate": 0 * ureg.MHz / ureg.s,
        "detuning": 0 * ureg.MHz,
        "duration_no_scan": 0.1 * ureg.s,
        "rf_assist": {
            "use": False,
            "use_sequential": True,
            "name": "rf_coil",
            "transition": "ab",
            "offset_start": 30 * ureg.kHz, #30 * ureg.kHz, #-110 * ureg.kHz
            "offset_end": 170 * ureg.kHz, #170 * ureg.kHz, #20 * ureg.kHz
            "amplitude": 1000,
            "duration": 5 * ureg.ms,
        }
    },
    "detect": {
        "transition": "bb",
        "trigger_channel": 2,
        "detunings": np.linspace(-1.9, 1.9, 20) * ureg.MHz,
        "randomize": False,
        "on_time": 10 * ureg.us,
        "off_time": 2 * ureg.us,
        "chasm_repeats": 100,  # change the names of detection repeats
        "antihole_repeats": 100,
        "rf_repeats": 50,
    },
    "rf": {
        "name": "rf_coil",
        "transition": "ab",
        "amplitude_1": 2000,  # 4200
        "amplitude_2": 800,  # 1100
        "offset_1": -46 * ureg.kHz,
        "offsets_2": np.arange(-208.5 - scan_range, -208.5 + scan_range, scan_step) * ureg.kHz,
        "frequency_1_span": 0 * ureg.kHz,
        "frequency_2_span": 0 * ureg.kHz,
        "detuning_1": 0 * ureg.kHz,
        "detuning_2": 0 * ureg.kHz,
        "pulse_1_time": 0.075 * ureg.ms,
        "pulse_2_time": 0.2 * ureg.ms,
        "delay_time": 1 * ureg.ms,
        "phase_noise": 0.,
    },
}
default_sequence = RFSatAbsSpectroscopyConsecutative(
    ao_parameters=default_params["ao"],
    eos_parameters=default_params["eos"],
    field_plate_parameters=default_params["field_plate"],
    chasm_parameters=default_params["chasm"],
    antihole_parameters=default_params["antihole"],
    rf_parameters=default_params["rf"],
    detect_parameters=default_params["detect"],
)
default_sequence.setup_sequence()

digitizer_time_s = default_sequence.analysis_parameters["digitizer_duration"].to("s").magnitude
sample_rate = 25000000
dg.set_acquisition_config(
    num_channels=2,
    sample_rate=sample_rate,
    segment_size=int(digitizer_time_s * sample_rate),
    segment_count=default_sequence.num_of_records() * default_params["repeats"]
)
dg.set_channel_config(channel=1, range=2)
dg.set_channel_config(channel=2, range=0.5)
dg.set_trigger_source_edge()
dg.write_configs_to_device()


## scan

params = default_params.copy()
rf_offset_2s = np.arange(-46 - scan_range, -46 + scan_range, scan_step)
rf_offset_2s *= ureg.kHz
params["rf"]["amplitude_1"] = 2000
params["rf"]["amplitude_2"] = 800
params["rf"]["pulse_1_time"] = 0.075 * ureg.ms
params["rf"]["pulse_2_time"] = 0.2 * ureg.ms
params["rf"]["offsets_2"] = rf_offset_2s
params["field_plate"]["amplitude"] = 4500
run_experiment(params)



center_freqs = [258, -213, -46]  # -208, -41, 263
amplitudes = [2800, 2800, 800] #[4200, 800, 4200]
chasm_scan_rates = [30, 300, 900]

for scan_rate in chasm_scan_rates:
    for kk in range(200):
        for ll in range(len(center_freqs)):
            print(ll)
            params = default_params.copy()
            center_freq = center_freqs[ll]
            amplitude = amplitudes[ll]
            rf_offset_2s = np.arange(center_freq - scan_range, center_freq + scan_range, scan_step)
            rf_offset_2s *= ureg.kHz
            params["chasm"]["scan_rate"]
            params["rf"]["amplitude_2"] = amplitude
            params["rf"]["offsets_2"] = rf_offset_2s
            params["field_plate"]["amplitude"] = 4500
            print("positive")
            run_experiment(params)
#
#         print("negative")
#         params["field_plate"]["amplitude"] = -4500
#         run_experiment(params)
#
#
# print("start")
## empty