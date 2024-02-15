import time
from datetime import datetime

import numpy as np
from onix.headers.awg.M4i6622 import M4i6622
from onix.headers.pcie_digitizer.pcie_digitizer import Digitizer
from onix.sequences.rf_spectroscopy import RFSpectroscopy
from onix.units import ureg
from onix.experiments.shared import shared_params, run_save_sequences, setup_digitizer

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
    sequence = RFSpectroscopy(  # Only change the part that changed
        ao_parameters=params["ao"],
        eos_parameters=params["eos"],
        field_plate_parameters=params["field_plate"],
        chasm_parameters=params["chasm"],
        antihole_parameters=params["antihole"],
        rf_parameters=params["rf"],
        detect_parameters=params["detect"],
    )

    return run_save_sequences(sequence, m4i, dg, params)

## parameters
default_params = {
    "name" : "RF Spectroscopy",
    "antihole": {
        "transitions": ["ac", "ca"],
        "scan": 0 * ureg.MHz,
        "scan_rate": 0 * ureg.MHz / ureg.s,
        "detuning": 0 * ureg.MHz,
        "duration_no_scan": 0.2 * ureg.s,
        "rf_assist": {
            "use": False,
            "use_sequential": False,
            "name": "rf_coil",
            "transition": "ab",

            # vertical transitions
            "offset_start": -100 * ureg.kHz, #-110, 30
            "offset_end": 20 * ureg.kHz, #20, 170

            # a bbar
            # "offset_start": 245 * ureg.kHz, #-220
            # "offset_end": 275 * ureg.kHz, #-190

            "amplitude": 2000,
            "duration": 5 * ureg.ms,
        }
    },
    "detect": {
        "transition": "bb",
        "trigger_channel": 2,
        "detunings": np.linspace(-2, 2, 20) * ureg.MHz,
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
        "amplitude": 4000,  # 4200
        "offset": -210 * ureg.kHz,
        "detuning": 0 * ureg.kHz,
        "duration": 0.5 * ureg.ms,
    },
}

default_params.update(shared_params)

default_sequence = RFSpectroscopy(
    ao_parameters=default_params["ao"],
    eos_parameters=default_params["eos"],
    field_plate_parameters=default_params["field_plate"],
    chasm_parameters=default_params["chasm"],
    antihole_parameters=default_params["antihole"],
    rf_parameters=default_params["rf"],
    detect_parameters=default_params["detect"],
)
default_sequence.setup_sequence()

setup_digitizer(dg, default_params["repeats"], default_sequence)

## timeit

start_time = time.time()

## scan delay between rf assist no rf assist
# params = default_params.copy()
# delay_times = np.logspace(-1, 3.5, 120)
# first_data_id = None
#
# for kk in range(len(delay_times)):
#     params["delay_time"] = delay_times[kk]
#
#     # rf assist
#     params["antihole"]["rf_assist"]["use_sequential"] = True
#     data_id = run_experiment(params)
#
#     if first_data_id == None:
#         first_data_id = data_id
#
#     time.sleep(delay_times[kk])
#
#     # no rf assist
#     params["antihole"]["rf_assist"]["use_sequential"] = False
#     data_id = run_experiment(params)



## repeat single parameter
# rf_frequencies = np.linspace(100, 100, 1000)
# rf_frequencies *= ureg.kHz
# params = default_params.copy()
# first_data_id = None
# for kk in range(len(rf_frequencies)):
#     params["rf"]["offset"] = rf_frequencies[kk]
#     data_id = run_experiment(params)
#     print(data_id)
#     if first_data_id == None:
#         first_data_id = data_id

## scan freq

# params = default_params.copy()
# first_data_id = None
#
# params["rf"]["amplitude"] = 2000
# params["rf"]["duration"] = 0.07 * ureg.ms
#
# rf_frequencies = np.arange(-140, 190, 10)
# rf_frequencies *= ureg.kHz
# for kk in range(len(rf_frequencies)):
#     params["rf"]["offset"] = rf_frequencies[kk]
#     data_id = run_experiment(params)
#     print(data_id)
#     if first_data_id == None:
#         first_data_id = data_id
#
#
# params["rf"]["amplitude"] = 4200
# params["rf"]["duration"] = 0.15 * ureg.ms
#
# rf_frequencies = np.append(np.arange(-300, -140, 10), np.arange(190, 350, 10))
# rf_frequencies *= ureg.kHz
# for kk in range(len(rf_frequencies)):
#     params["rf"]["offset"] = rf_frequencies[kk]
#     data_id = run_experiment(params)
#     print(data_id)
#
#
# params = default_params.copy()
# first_data_id = None
#
# rf_frequencies = np.arange(-300, 350, 10)
# rf_frequencies *= ureg.kHz
# for kk in range(len(rf_frequencies)):
#     params["rf"]["offset"] = rf_frequencies[kk]
#     data_id = run_experiment(params)
#     print(data_id)
#     if first_data_id == None:
#         first_data_id = data_id

## scan time
rf_times = np.linspace(0.01, 1, 10) * ureg.ms
params = default_params.copy()
first_data_id = None

for kk in range(len(rf_times)):
    params["rf"]["duration"] = rf_times[kk]
    data_id = run_experiment(params)
    print(data_id)
    if first_data_id == None:
        first_data_id = data_id
        params["first_data_id"] = data_id

## scan antihole and time
# rf_times = np.linspace(0.01, 0.5, 10) * ureg.ms
# antihole_times = np.array([0.03, 0.1, 0.3]) * ureg.s
# params = default_params.copy()
# first_data_id = None
#
# for kk in range(len(rf_times)):
#     params["rf"]["duration"] = rf_times[kk]
#     for antihole_time in antihole_times:
#         params["antihole"]["duration_no_scan"] = antihole_time
#         data_id = run_experiment(params)
#         print(data_id)
#         if first_data_id == None:
#             first_data_id = data_id

## print info
end_time = time.time()

print("\n")
print(f"Took {(end_time-start_time):.2f} s = {(end_time-start_time) / 60:.2f} min = {(end_time-start_time) / 3600:.2f} h")
print(f"data = (first, last)")
print(f"data = ({first_data_id}, {data_id})")

## test


## empty