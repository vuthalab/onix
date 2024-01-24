import time

import numpy as np
from onix.headers.awg.M4i6622 import M4i6622
from onix.headers.pcie_digitizer.pcie_digitizer import Digitizer
from onix.sequences.antihole_optimization import AntiholeOptimization
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
    sequence = AntiholeOptimization(  # Only change the part that changed
        ao_parameters=params["ao"],
        eos_parameters=params["eos"],
        chasm_parameters=params["chasm"],
        antihole_parameters=params["antihole"],
        detect_parameters=params["detect"],
    )

    return run_save_sequences(sequence, m4i, dg, params)

## parameters
default_params = {
    "name" : "Antihole Optimization",
    "antihole": {
        "transitions": ["ac", "ca"],
        "scan": 0 * ureg.MHz,
        "scan_rate": 0 * ureg.MHz / ureg.s,
        "detuning": 0 * ureg.MHz,
        "duration_no_scan": 0.1 * ureg.s,
        "rf_assist": {
            "use": False,
            "use_sequential": False,
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

default_sequence = AntiholeOptimization(
    ao_parameters=default_params["ao"],
    eos_parameters=default_params["eos"],
    chasm_parameters=default_params["chasm"],
    antihole_parameters=default_params["antihole"],
    detect_parameters=default_params["detect"],
)
default_sequence.setup_sequence()

setup_digitizer(dg, default_params["repeats"], default_sequence)

## Optimization parameters and ranges
eos_ac_offset_range_MHz = (-298, -302)
eos_ca_offset_range_MHz = (-298, -302)

eos_ac_amplitude_range = (500, 2000)
eos_ca_amplitude_range = (500, 2000)

antihole_ac_piecewise_time_range = (1e-3, 20e-3)
antihole_ca_piecewise_time_range = (1e-3, 20e-3)

antihole_time_range = (50e-3, 400e-3)

