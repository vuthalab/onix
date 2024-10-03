import numpy as np

from onix.control.exp_definition_creator import ExpDefinitionCreator
from onix.control.exps.shared import update_parameters_from_shared
from onix.units import ureg


parameters = {
    "field_plate": {
        "channel_name": "field_plate",
        "polarity": 1,
        "low_voltage": -0.0013 * ureg.V,  # AWG output before the HV amplifier
        "high_voltage": 1.75 * ureg.V,  # compensates the dc offset.
        "amplifier_voltage_gain": 50,
        "voltage_to_field": 1 / (0.87 * ureg.cm),
        "dipole_moment": 27.7 * ureg.kHz / (ureg.V / ureg.cm),
        "rise_ramp_time": 3 * ureg.ms,  # ramp time from low to high.
        "rise_delay_time": 2 * ureg.ms,  # wait time in the high state before voltage is stabilized.
        "fall_ramp_time": 0 * ureg.ms,  # ramp time from high to low.
        "fall_delay_time": 2 * ureg.ms,  # wait time in the low state before voltage is stabilized.
        "use": True,
        "during": ["chasm", "detect"],
        "negative_Pi_first": True,  # if True, scans the Pi=-1 ions before the Pi=+1 ions.
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


## scan overnight
# phases = np.linspace(0, 2 * np.pi, 8, endpoint=False)
# Sigmas = [-1, 1]
# polarities = [-1, 1]
# for kk in range(7):
#     for polarity in polarities:
#         exp_parameters["field_plate"]["polarity"] = polarity
#         edc = ExpDefinitionCreator(
#             "LF Ramsey",
#             sequence,
#             exp_parameters,
#         )
#         iterate_param_values = []
#         for Sigma in Sigmas:
#             for phase in phases:
#                 iterate_param_values.append((phase, Sigma, Sigma, polarity))
#
#         edc.iterate_parameters(
#             [
#                 ("lf", "ramsey", "phase"),
#                 ("lf", "ramsey", "Sigma"),
#                 ("lf", "equilibrate", "Sigma"),
#             ],
#             iterate_param_values,
#             repeats=200,
#         )
##
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
    repeats=50,
)