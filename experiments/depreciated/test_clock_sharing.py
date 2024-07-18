import time

import numpy as np
from onix.sequences.test_clock_sharing import ClockSharingTest
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


# function to run the experiment
def get_sequence(params):
    sequence = ClockSharingTest(params)
    return sequence


# parameters
default_params = {
    "name": "ClockSharingTest",
    "sequence_repeats_per_transfer": 1,
    "data_transfer_repeats": 1,
    "chasm": {
        "transitions": ["bb"],  # , "rf_both"
        "scan": 2.5 * ureg.MHz,
        "durations": 0 * ureg.us,
        "repeats": 0,
        "detunings": 0 * ureg.MHz,
        "ao_amplitude": 2000,
    },
    "antihole": {
        "transitions": ["ac", "ca"],  # , "rf_b" (for rf assist)
        "durations": [0 * ureg.ms, 0 * ureg.ms],
        "repeats": 0,
        "ao_amplitude": 800,
    },
    "detect": {
        # np.array([-2, 0]) * ureg.MHz,
        "detunings": np.linspace(-2.5, 2.5, 10) * ureg.MHz,
        "on_time": 0 * ureg.us,
        "off_time": 0 * ureg.us,
        "cycles": {
            "chasm": 0,
            "antihole": 0,
            "rf": 0,
        },
        "delay": 0 * ureg.us,
    },
    "rf": {
        "amplitude": 4000,
        "T_0": 10 * ureg.ms,
        "T_e": 0 * ureg.ms,
        "T_ch": 0 * ureg.ms,
        "center_detuning": 0 * ureg.kHz,
        "scan_range": 0 * ureg.kHz,
        "use_hsh": True,
    },
    "test_params": {
        "channel1": 0,
        "channel2": 4,
        "amplitude": 4000,
        "frequency": 1*ureg.MHz,
        "duration": 10*ureg.us
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
)

params = default_params.copy()
data = run_sequence(sequence, params)
