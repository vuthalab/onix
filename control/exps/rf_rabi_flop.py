import numpy as np

from onix.control.exp_definition_creator import ExpDefinitionCreator
from onix.control.exps.shared import update_parameters_from_shared
from onix.units import ureg


parameters = {
    "field_plate": {
        "use": True,
    },
    "chasm": {
        "transitions": "ac",  # only burns a chasm on a -> c'
        "detunings": 0 * ureg.MHz,
        "scans": 5 * ureg.MHz,
        "amplitudes": 0.15 * ureg.V,
        "durations": 1 * ureg.ms,
        "repeats": 50,
    },
    "antihole": {
        "transitions": ["ac", "cb"],
        "detunings": 0 * ureg.MHz,
        "amplitudes": 0.15 * ureg.V,
        "durations": 1 * ureg.ms,
        "repeats": 50,
    },
    "detect": {
        "mode": "abs",
        "abs": {
            "detunings": np.linspace(-4.5, 4.5, 35) * ureg.MHz,
            "on_time": 5 * ureg.us,
            "off_time": 1 * ureg.us,
            "delay": 8 * ureg.us,
            "amplitude": 17 * ureg.mV,
            "repeats": 512,
        },
    },
    "rf": {
        "rabi": {
            "detuning": 0 * ureg.kHz,
            "amplitude": 0.6 * ureg.V,
            "duration": 1 * ureg.ms,
        },
    },
}


sequence = [
    "chasm",
    "antihole",
    "rf_sweep_abar_to_bbar",
    "rf_sweep_a_to_b",
    "detect_1",
    "rf_rabi",
    "detect_2",
]
exp_parameters = update_parameters_from_shared(parameters)

edc = ExpDefinitionCreator(
    "RF Rabi Flop",
    sequence,
    exp_parameters,
)
# above ~24 scanned values it may crash.
iterate_param_values = [(kk * ureg.kHz, ) for kk in np.linspace(-300, 300, 60)]
group_size = 20
for kk in range(0, len(iterate_param_values), group_size):
    start = kk
    stop = kk + group_size
    if stop > len(iterate_param_values):
        stop = len(iterate_param_values)
    edc.iterate_parameters(
        [("rf", "rabi", "detuning")],
        iterate_param_values[start:stop],
    )