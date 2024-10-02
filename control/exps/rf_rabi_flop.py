import numpy as np

from onix.control.exp_definition_creator import ExpDefinitionCreator
from onix.control.exps.shared import update_parameters_from_shared
from onix.units import ureg


parameters = {
    "field_plate": {
        "low_voltage": -0.002 * ureg.V,  # AWG output before the HV amplifier
        "high_voltage": 1.25 * ureg.V,  # compensates the dc offset.
        "use": False,  # uses the field plate in the experiment.
        "during": ["chasm", "detect"],
    },
    "chasm": {
        "transitions": "ac",  # only burns a chasm on a -> c'
        "detunings": 0 * ureg.MHz,
        "scans": 4 * ureg.MHz,
        "amplitudes": 0.15 * ureg.V,
        "durations": 1 * ureg.ms,
        "repeats": 25,
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
            "detunings": np.linspace(-3.5, 3.5, 35) * ureg.MHz,
            "on_time": 5 * ureg.us,
            "off_time": 1 * ureg.us,
            "delay": 8 * ureg.us,
            "amplitude": 15 * ureg.mV,
            "repeats": 512,
        },
    },
    "rf": {
        "avg_center_frequency": 119.23 * ureg.MHz,
        "sweep": {
            "detuning_abar_to_bbar": -60 * ureg.kHz,
            "detuning_a_to_b": 55 * ureg.kHz,
            "amplitude": 0.3 * ureg.V,
            "T_0": 0.3 * ureg.ms,
            "T_e": 0.15 * ureg.ms,
            "T_ch": 25 * ureg.ms,
            "scan": 30 * ureg.kHz,
        },
        "rabi": {
            "detuning": 0 * ureg.kHz,
            "amplitude": 0.3 * ureg.V,
            "duration": 10 * ureg.ms,
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
iterate_param_values = [(kk * ureg.kHz, ) for kk in np.linspace(-300, 300, 50)]
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