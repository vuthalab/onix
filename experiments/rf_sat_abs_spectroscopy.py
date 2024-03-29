import time

import numpy as np
from onix.data_tools import save_experiment_data
from onix.headers.awg.M4i6622 import M4i6622
from onix.headers.pcie_digitizer.pcie_digitizer import Digitizer
from onix.sequences.rf_sat_abs_spectroscopy import RFSatAbsSpectroscopy
from onix.experiments.helpers import data_averaging
from onix.units import ureg

from onix.headers.wavemeter import wavemeter

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

try:
    wm
    print("wm is already defined.")
except Exception:
    wm = wavemeter.WM()


## function to run the experiment
def run_experiment(params):
    sequence = RFSatAbsSpectroscopy(  # Only change the part that changed
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
    name = "RF Saturation Absorption Spectroscopy"
    data_id = save_experiment_data(name, data, headers)
    print(data_id)
    #print()


## parameters
default_params = {
    "wm_channel": 5,
    "repeats": 20,
    "ao": {
        "name": "ao_dp",
        "order": 2,
        "frequency": 75 * ureg.MHz,  # TODO: rename it to "center_frequency"
        "amplitude": 2000,
        "detect_amplitude": 600,
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
        "amplitude": 4500,
        "stark_shift": 2 * ureg.MHz,
        "padding_time": 5 * ureg.ms,
    },
    "chasm": {
        "transition": "bb",
        "scan": 3 * ureg.MHz,
        "scan_rate": 10 * ureg.MHz / ureg.s,
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
            "offset_start": 30 * ureg.kHz, #-110 * ureg.kHz
            "offset_end": 170 * ureg.kHz, #20 * ureg.kHz
            "amplitude": 2000,
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
        "rf_repeats": 100,
    },
    "rf": {
        "name": "rf_coil",
        "transition": "ab",
        "amplitude_1": 500,  # 4200
        "amplitude_2": 500,  # 1100
        "offset_1": -40 * ureg.kHz,
        "offset_2": -40 * ureg.kHz,
        "frequency_1_span": 0 * ureg.kHz,
        "frequency_2_span": 0 * ureg.kHz,
        "detuning_1": 0 * ureg.kHz,
        "detuning_2": 0 * ureg.kHz,
        "pulse_1_time": 0.4 * ureg.ms,
        "pulse_2_time": 0.4 * ureg.ms,
        "delay_time": 0.2 * ureg.ms,
        "phase_noise": 0.,
    },
}
default_sequence = RFSatAbsSpectroscopy(
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


## wavemeter scan
# def set_wavemeter_to_setpoint_and_wait(setpoint):
#     wm.set_lock_setpoint(5, setpoint)
#     freq = wm.read_frequency(5)
#     while not isinstance(freq, float) or abs(wm.read_frequency(5) - setpoint) > 0.001:
#         time.sleep(1)
#         freq = wm.read_frequency(5)
#     time.sleep(20)
#     print(wm.read_frequency(5))
#
# ## wavemeter scan and experiment scan
# wavemeter_setpoints = [516847.85, 516848.05, 516847.55]
# scan_range = 20
# scan_step = 3
#
# center_freqs = [258, -213, -46]  # -208, -41, 263
# amplitudes = [4200, 4200, 800] #[4200, 800, 4200]
#
# for setpoint in wavemeter_setpoints:
#     set_wavemeter_to_setpoint_and_wait(setpoint)
#
#     for kk in range(4):
#         for ll in range(len(center_freqs)):
#             center_freq = center_freqs[ll]
#             rf_offset_2s = np.arange(center_freq - scan_range, center_freq + scan_range, scan_step)
#             rf_offset_2s *= ureg.kHz
#             for mm in range(len(rf_offset_2s)):
#                 params = default_params.copy()
#                 params["rf"]["amplitude_1"] = 2000
#                 params["rf"]["pulse_1_time"] = 0.09 * ureg.ms
#                 params["rf"]["amplitude_2"] = amplitudes[ll]
#                 params["rf"]["pulse_2_time"] = 0.25 * ureg.ms
#                 params["rf"]["offset_2"] = rf_offset_2s[mm]
#
#                 params["field_plate"]["amplitude"] = 4500
#                 run_experiment(params)
#                 params["field_plate"]["amplitude"] = -4500
#                 run_experiment(params)
# set_wavemeter_to_setpoint_and_wait(516847.4)

## temp
scan_range = 5
scan_step = 1
pump_offset_center = -40
pump_offset_range = 1
pump_offset_step = 10
b_bbar = -167
a_abar = 323
probe_vertical_power = 500
probe_cross_power = 2000

params = default_params.copy()
for pump_offset in np.arange(pump_offset_center - pump_offset_range, pump_offset_center + pump_offset_range, pump_offset_step):
    params["rf"]["offset_1"] = pump_offset * ureg.kHz
    print(pump_offset)
    for probe_offset in np.arange(pump_offset - scan_range, pump_offset + scan_range, scan_step):
        params["rf"]["offset_2"] = probe_offset * ureg.kHz
        params["rf"]["amplitude_2"] = probe_vertical_power
        run_experiment(params)
    for probe_offset in np.arange(pump_offset + b_bbar - scan_range, pump_offset + b_bbar + scan_range, scan_step):
        params["rf"]["offset_2"] = probe_offset * ureg.kHz
        params["rf"]["amplitude_2"] = probe_cross_power
        run_experiment(params)
    for probe_offset in np.arange(pump_offset + a_abar - scan_range, pump_offset + a_abar + scan_range, scan_step):
        params["rf"]["offset_2"] = probe_offset * ureg.kHz
        params["rf"]["amplitude_2"] = probe_cross_power
        run_experiment(params)

## scan
# scan_range = 10
# scan_step = 1
#
# center_freqs = [258, -213, -46]  # -208, -41, 263
# amplitudes = [1400, 1400, 400] #[4200, 800, 4200]
#
# for kk in range(1500):
#     for ll in range(len(center_freqs)):
#         center_freq = center_freqs[ll]
#         rf_offset_2s = np.arange(center_freq - scan_range, center_freq + scan_range, scan_step)
#         rf_offset_2s *= ureg.kHz
#         for mm in range(len(rf_offset_2s)):
#             params = default_params.copy()
#             params["rf"]["amplitude_2"] = amplitudes[ll]
#             params["rf"]["offset_2"] = rf_offset_2s[mm]
#
#             params["field_plate"]["amplitude"] = 4500
#             run_experiment(params)
#             params["field_plate"]["amplitude"] = -4500
#             run_experiment(params)


# rf_offset_2s = np.arange(-41 - scan_range, -41 + scan_range, scan_step)
# rf_offset_2s *= ureg.kHz
# params = default_params.copy()
# params["rf"]["amplitude_2"] = 700
# params["rf"]["pulse_2_time"] = 0.4 * ureg.ms
# for kk in range(len(rf_offset_2s)):
#     params["rf"]["offset_2"] = rf_offset_2s[kk]
#     run_experiment(params)
#
# rf_offset_2s = np.arange(263 - scan_range, 263 + scan_range, scan_step)
# rf_offset_2s *= ureg.kHz
# params = default_params.copy()
# params["rf"]["amplitude_2"] = 4200
# params["rf"]["pulse_2_time"] = 0.45 * ureg.ms
# for kk in range(len(rf_offset_2s)):
#     params["rf"]["offset_2"] = rf_offset_2s[kk]
#     run_experiment(params)

## empty