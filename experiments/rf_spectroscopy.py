import time

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

    run_save_sequences(sequence, m4i, dg, params)

## parameters
default_params = {
    "name" : "RF Spectroscopy",
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
            "offset_start": -110 * ureg.kHz, #-110, 30
            "offset_end": 20 * ureg.kHz, #20, 170
            "amplitude": 1000,
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
        "amplitude": 2000,  # 4200
        "offset": 100 * ureg.kHz,
        "detuning": 0 * ureg.kHz,
        "duration": 0.03 * ureg.ms,
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

setup_digitizer(dg, default_params, default_sequence)

## scan freq
# rf_frequencies = np.arange(-250, 300, 10)
# rf_frequencies *= ureg.kHz
# params = default_params.copy()
# for kk in range(len(rf_frequencies)):
#     params["rf"]["offset"] = rf_frequencies[kk]
#     run_experiment(params)


## scan time
rf_times = np.linspace(0.01, 0.3, 10)
rf_times *= ureg.ms
params = default_params.copy()

first_data_id = None

for kk in range(len(rf_times)):
    params["rf"]["duration"] = rf_times[kk]
    data_id = run_experiment(params)
    print(f"data number: {data_id}")
    if first_data_id == None:
        first_data_id = data_id

print(f"first data id = {first_data_id}\nlast data id = {data_id}")

## empty