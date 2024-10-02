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
    "lf_rabi",
    "rf_sweep_abar_to_bbar",
    "detect_2",
]
exp_parameters = update_parameters_from_shared(parameters)

edc = ExpDefinitionCreator(
    "LF Rabi flop",
    sequence,
    exp_parameters,
)
#edc.schedule()
# above ~24 scanned values it may crash.
for kk in range(10):
    edc.iterate_parameters(
        [("lf", "rabi", "detuning")],
        [(kk, ) for kk in np.linspace(-10, 10, 10) * ureg.kHz],
    )