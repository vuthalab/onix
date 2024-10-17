import numpy as np

from onix.control.exp_definition_creator import ExpDefinitionCreator
from onix.control.exps.shared import update_parameters_from_shared
from onix.units import ureg


parameters = {
    "field_plate": {
        "use": True,
        "high_voltage": 5 * ureg.V,  # compensates the dc offset.
        "during": ["chasm", "detect"],
    },
    "chasm": {
        "transitions": ["ac", "cb"],  # only burns a chasm on a -> c'
        "detunings": 0 * ureg.MHz,
        "scans": 5 * ureg.MHz,
        "amplitudes": 0.15 * ureg.V,
        "durations": 1 * ureg.ms,
        "repeats": 2000,
    },
    "antihole": {
        "transitions": ["ac"],
        "detunings": 0 * ureg.MHz,
        "amplitudes": 0.01 * ureg.V,
        "durations": 1 * ureg.ms,
        "repeats": 5000,
    },
    "detect": {
        "mode": "abs",
        "abs": {
            "detunings": np.linspace(-3, 3, 120) * ureg.MHz,
            "on_time": 5 * ureg.us,
            "off_time": 1 * ureg.us,
            "delay": 8 * ureg.us,
            "amplitude": 17 * ureg.mV,
            "repeats": 64,
        },
    },
    "rf": {
        "channel_name": "rf_coil",
        "avg_center_frequency": 119.225 * ureg.MHz,
        "rabi": {
            "detuning": 0 * ureg.kHz,
            "amplitude": 0 * ureg.mV,
            "duration": 10 * ureg.ms,
        },
    },
}


sequence = [
    "chasm",
    "rf_sweep_abar_to_bbar",
    "rf_sweep_a_to_b",
    "delay_2000",
    "antihole",
    "detect_1",
    "detect_2",
    "detect_3",
]
exp_parameters = update_parameters_from_shared(parameters)

edc = ExpDefinitionCreator(
    "Antihole Spectroscopy",
    sequence,
    exp_parameters,
)
edc.schedule()

