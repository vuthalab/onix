import numpy as np

from onix.control.exp_definition_creator import ExpDefinitionCreator
from onix.control.exps.shared import update_parameters_from_shared
from onix.units import ureg


parameters = {
    "antihole": {
        "repeats": 50,
    },
    "detect": {
        "abs": {
            "delay": 8 * ureg.us,
            "repeats": 512,
        },
    },
}


sequence = [
    "chasm",
    "antihole",
    "detect_1",
    "lf_equilibrate",
    "rf_sweep_abar_to_bbar",
    "lf_ramsey",
    "rf_sweep_abar_to_bbar",
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
)