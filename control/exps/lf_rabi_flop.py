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
        "scans": 5 * ureg.MHz,  # scans +/-5 MHz in the optical frequency.
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
    "lf": {
        "channel_name": "rf_coil",
        "equilibrate": {
            "center_frequency": 139 * ureg.kHz,
            "Sigma": 0,
            "Zeeman_shift_along_b": 5 * ureg.kHz,
            "piov2_amplitude": 250 * ureg.mV,
            "piov2_duration": 19 * ureg.us,
            "use_composite": True,
            "composite_segments": 3,
        },
        "rabi": {
            "center_frequency": 139 * ureg.kHz,
            "Sigma": 0,  # 0, +1, -1.
            "Zeeman_shift_along_b": 5 * ureg.kHz,
            "detuning": 0 * ureg.kHz,
            "amplitude": 1 * ureg.mV,
            "duration": 5 * ureg.ms,
        },
    },
    "rf": {
        "avg_center_frequency": 119.225 * ureg.MHz,
        "sweep": {
            "detuning_abar_to_bbar": -55 * ureg.kHz,
            "detuning_a_to_b": 55 * ureg.kHz,
            "amplitude": 0.25 * ureg.V,
            "T_0": 0.3 * ureg.ms,
            "T_e": 0.15 * ureg.ms,
            "T_ch": 25 * ureg.ms,
            "scan": 30 * ureg.kHz,
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
# above ~24 scanned values it may crash.

## freq scan
iterate_param_values = [(kk * ureg.kHz, ) for kk in np.linspace(7, -7, 100)]
group_size = 10
for kk in range(0, len(iterate_param_values), group_size):
    start = kk
    stop = kk + group_size
    if stop > len(iterate_param_values):
        stop = len(iterate_param_values)
    edc.iterate_parameters(
        [("lf", "rabi", "detuning")],
        iterate_param_values[start:stop],
    )

## duration scan
# iterate_param_values = [(kk * ureg.us, ) for kk in np.linspace(0, 100, 40)]
# group_size = 20
# for kk in range(0, len(iterate_param_values), group_size):
#     start = kk
#     stop = kk + group_size
#     if stop > len(iterate_param_values):
#         stop = len(iterate_param_values)
#     edc.iterate_parameters(
#         [("lf", "rabi", "duration")],
#         iterate_param_values[start:stop],
#     )