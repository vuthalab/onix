import time

import numpy as np
from onix.sequences.lf_spectroscopy import LFSpectroscopy
from onix.units import ureg
from onix.experiments.shared import (
    m4i,
    dg,
    update_parameters_from_shared,
    setup_digitizer,
    run_sequence,
    save_data,
)
from tqdm import tqdm


## function to run the experiment
def get_sequence(params):
    sequence = LFSpectroscopy(params)
    return sequence


## parameters
default_params = {
    "name": "LF Spectroscopy",
    "sequence_repeats_per_transfer": 1,
    "data_transfer_repeats": 1,
    "rf": {
        "amplitude": 4000,
        "T_0": 10e-3,
        "T_e": 10e-3,
        "T_ch": 30e-3,
        "center_frequency": 20e3,
        "scan_range": 3000,
        },
    "lf": {
        "center_frequency": 167 * ureg.kHz,
        "detuning": 0 * ureg.kHz,
        "duration": 50 * ureg.ms,
        "amplitude": 4000,
    },
    "detect": {
        "detunings": np.array([-2, 0]) * ureg.MHz,
        "on_time": 2 * ureg.us,
        "off_time": 0.5 * ureg.us,
        "cycles": {
            "chasm": 0,
            "antihole": 64,
            "rf": 64,
        },
        "delay": 8 * ureg.us,
    },
    "digitizer": {
        "sample_rate": 25e6,
        "ch1_range": 2,
        "ch2_range": 2,
    },
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
)

## test
params = default_params.copy()
sequence = get_sequence(params)
data = run_sequence(sequence, params)
# data_id = save_data(sequence, params, *data)
# print(data_id)