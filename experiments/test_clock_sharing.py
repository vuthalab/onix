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


# function to run the experiment
def get_sequence(params):
    sequence = LFSpectroscopy(params)
    return sequence


# parameters
default_params = {
    "name": "LF Spectroscopy",
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
        "transitions": ["ac", "ca", "rf_b"],  # , "rf_b" (for rf assist)
        "durations": [0 * ureg.ms, 0 * ureg.ms, 0 * ureg.ms],
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
        "T_0": 0 * ureg.ms,
        "T_e": 0 * ureg.ms,
        "T_ch": 0 * ureg.ms,
        "center_detuning": 0 * ureg.kHz,
        "scan_range": 0 * ureg.kHz,
        "use_hsh": True,
    },
    "test_params": {
        "channel1": 0,
        "channel2": 4,
        "amplitude": 4000,  # what units?
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

# Scan the RF Center Detunings
# params = default_params.copy()
# rf_frequencies = np.arange(-200, 200, 20)
# rf_frequencies *= ureg.kHz
# for kk in range(len(rf_frequencies)):
#     params["rf"]["center_detuning"] = rf_frequencies[kk]
#     sequence = get_sequence(params)
#     data = run_sequence(sequence, params)
#     data_id = save_data(sequence, params, *data)
#     if kk == 0:
#         first_data_id = data_id
#     elif kk == len(rf_frequencies) - 1:
#         last_data_id = data_id
# print(f"({first_data_id}, {last_data_id})")


# Scan the LF Detunings
params = default_params.copy()
lf_frequencies = np.arange(-20, 20, 0.25)
lf_frequencies *= ureg.kHz
for kk in tqdm(range(len(lf_frequencies))):
    params["lf"]["detuning"] = lf_frequencies[kk]
    sequence = get_sequence(params)
    data = run_sequence(sequence, params)
    data_id = save_data(sequence, params, *data)
    # one second delay between each step to prevent heating issues
    time.sleep(1)
    if kk == 0:
        first_data_id = data_id
    elif kk == len(lf_frequencies) - 1:
        last_data_id = data_id
print(f"({first_data_id}, {last_data_id})")
