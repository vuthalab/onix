import numpy as np
from onix.sequences.rf_spectroscopy import RFSpectroscopy
from onix.units import ureg
from onix.experiments.shared import (
    m4i,
    dg,
    wm,
    update_parameters_from_shared,
    setup_digitizer,
    run_sequence,
    save_data,
)

## function to run the experiment
def get_sequence(params):
    sequence = RFSpectroscopy(params)
    return sequence


## parameters
default_params = {
    "name": "Inhomogeneous Scan",
    "sequence_repeats_per_transfer": 1,
    "data_transfer_repeats": 1,
    "eos": {
        "ac": {
            "amplitude": 0,
        },
        "bb": {
            "amplitude": 0,
        },
        "ca": {
            "amplitude": 0,
        },
    },
    "rf": {
        "amplitude": 0,
        "detuning": (65) * ureg.kHz,
        "duration": 0 * ureg.ms,
    },
    "chasm": {
        "repeats": 0,
        "ao_amplitude": 0,
    },
    "antihole": {
        "repeats": 0,
        "ao_amplitude": 0,
    },
    "detect": {
        "transition": "bb",
        "detunings": [0] * ureg.MHz, # np.array([-2, 0]) * ureg.MHz,
        "on_time": 2 * ureg.us, #5
        "off_time": 0.5 * ureg.us,
        "cycles": {
            "chasm": 0,
            "antihole": 64,
            "rf": 64,
        },
        "delay": 8 * ureg.us,
        "ao_amplitude": 450,
    },
    "field_plate": {
        "use": False,
    },
    "wavemeter": {
        "freq": 0,

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

while True:
    params = default_params.copy()
    sequence = get_sequence(params)
    freq = wm.read_frequency(5)
    params["wavemeter"]["freq"] = freq
    data = run_sequence(sequence, params)
    data_id = save_data(sequence, params, *data)
    print(data_id)