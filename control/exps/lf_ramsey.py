import numpy as np

from onix.control.exp_definition_creator import ExpDefinitionCreator
from onix.control.exps.shared import update_parameters_from_shared
from onix.units import ureg


parameters = {
    "field_plate": {
        "use": True,
    },
    "lf": {
        "equilibrate": {
            "center_frequency": 139.85 * ureg.kHz,
            "Sigma": 1,
            "Zeeman_shift_along_b": 4.15 * ureg.kHz,
            "detuning": 0 * ureg.kHz,
            "piov2_amplitude": 250 * ureg.mV,
            "piov2_duration": 19 * ureg.us,
            "use_composite": True,
            "composite_segments": 3,
        },
        "ramsey": {
            "center_frequency": 139.85 * ureg.kHz,
            "Sigma": 1,
            "Zeeman_shift_along_b": 4.15 * ureg.kHz,
            "detuning": 0 * ureg.kHz,
            "amplitude": 23 * ureg.mV,
            "piov2_time": 200 * ureg.us,
            "wait_time": 500 * ureg.us,
            "phase": 0,
        },
    },
}


sequence = [
    "chasm",
    "antihole",
    "detect_1",
    "lf_equilibrate",
    "rf_sweep_a_to_b",
    "lf_ramsey",
    "rf_sweep_a_to_b",
    "detect_2",
]
exp_parameters = update_parameters_from_shared(parameters)

edc = ExpDefinitionCreator(
    "LF Ramsey",
    sequence,
    exp_parameters,
)
# above ~24 scanned values it may crash.
phases = np.linspace(0, 2 * np.pi, 8, endpoint=False)
Sigmas = [-1, 1]
iterate_param_values = []
for Sigma in Sigmas:
    for phase in phases:
        iterate_param_values.append((phase, Sigma, Sigma))
edc.iterate_parameters(
    [
        ("lf", "ramsey", "phase"),
        ("lf", "ramsey", "Sigma"),
        ("lf", "equilibrate", "Sigma")
    ],
    iterate_param_values,
    repeats=5,
)