import time

import numpy as np
from onix.sequences.lf_spin_echo import LFSpinEcho
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
    sequence = LFSpinEcho(params)
    return sequence


## parameters
default_params = {
    "name": "LF Spin Echo",
    "sequence_repeats_per_transfer": 10,
    "data_transfer_repeats": 1,
    "chasm": {
        "transitions": ["bb"], #, "rf_both"
        "scan": 2.5 * ureg.MHz,
        "durations": [2 * ureg.ms],
        "repeats": 50,
        "detunings": 0 * ureg.MHz,
        "ao_amplitude": 2000,
    },
    "antihole": {
        "transitions": ["ac", "ca", "rf_bbar"], #(for rf assist)
        "durations": [1 * ureg.ms, 1 * ureg.ms, 5 * ureg.ms], #
        "repeats": 20,
        "ao_amplitude": 2000,
    },
    "detect": {
        "transition": "bb",
        "detunings": (np.linspace(-2., 2., 10)) * ureg.MHz, #np.array([-2, 0]) * ureg.MHz, #  # np.array([-2, 0]) * ureg.MHz,
        "on_time": 5 * ureg.us, #5
        "off_time": 1 * ureg.us,
        "cycles": {
            "chasm": 0,
            "antihole": 32,
            "rf": 32,
        },
        "delay": 8 * ureg.us,
        "ao_amplitude": 450,
    },
    "rf": {
        "amplitude": 6000,
        "T_0": 2 * ureg.ms,
        "T_e": 1 * ureg.ms,
        "T_ch": 15 * ureg.ms,
        "center_detuning": -60 * ureg.kHz,
        "scan_range": 50 * ureg.kHz,
        "cool_down_time": 500 * ureg.ms,
        "use_hsh": True,
        "pre_lf": True,
    },
    "lf": {
        "center_frequency": 302 * ureg.kHz, # 168 bbar -- 302 aabar (+- 3)
        "detuning": 0 * ureg.kHz,
        "amplitude": 6000, #32000
        "pi_time": 0.33 * ureg.ms,
        "piov2_time": 0.165 * ureg.ms,
        "delay_time": 0 * ureg.ms,
        "phase": 0,
        "phase_pi": 0,

        # "center_frequency": 119.23 * ureg.MHz,
        # "detuning": 0 * ureg.kHz,
        # "duration": 0.5 * ureg.ms,
        # "amplitude": 8000, #32000
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

params = default_params.copy()
phases = np.linspace(0, 2*np.pi, 10)
for kk in tqdm(range(len(phases))):
    params["lf"]["phase"] = phases[kk]
    sequence = get_sequence(params)
    data = run_sequence(sequence, params)
    data_id = save_data(sequence, params, *data)
    if kk == 0:
        first_data_id = data_id
        print(first_data_id)
    elif kk == len(phases) - 1:
        last_data_id = data_id
print(f"({first_data_id}, {last_data_id})")