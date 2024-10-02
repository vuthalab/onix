from copy import deepcopy
import numpy as np
from onix.units import ureg


_shared_parameters = {
    "hyperfine": {
        "7F0": {
            "a": 0 * ureg.MHz,
            "b": 119.2 * ureg.MHz,
            "c": 209.25 * ureg.MHz,
        },
        "5D0": {
            "a": 450.8 * ureg.MHz,
            "b": 191.3 * ureg.MHz,
            "c": 0 * ureg.MHz,
        }
    },
    "ao": {
        "channel_name": "ao_dp",  # links to the actual hardware channel.
        "order": 2,  # double-pass, upshifting.
        "rise_delay": 1.1 * ureg.us,
        "fall_delay": 0.6 * ureg.us,
        "frequency_ac": 80 * ureg.MHz,  # ao frequency of the a -> c' transition.
    },
    "digitizer": {
        "channel_name": "digitizer",
        "num_channels": 2,
        "sample_rate": 25e6,
        "ch1_range": 2,
        "ch2_range": 2,
    },
    "shutter": {
        "channel_name": "shutter",
        "rise_delay": 3 * ureg.ms,
        "fall_delay": 2 * ureg.ms,
    },
    "field_plate": {
        "channel_name": "field_plate",
        "low_voltage": -0.0013 * ureg.V,  # AWG output before the HV amplifier
        "high_voltage": 1.75 * ureg.V,  # compensates the dc offset.
        "amplifier_voltage_gain": 50,
        "voltage_to_field": 1 / (0.87 * ureg.cm),
        "dipole_moment": 27.7 * ureg.kHz / (ureg.V / ureg.cm),
        "rise_ramp_time": 3 * ureg.ms,  # ramp time from low to high.
        "rise_delay_time": 2 * ureg.ms,  # wait time in the high state before voltage is stabilized.
        "fall_ramp_time": 0 * ureg.ms,  # ramp time from high to low.
        "fall_delay_time": 2 * ureg.ms,  # wait time in the low state before voltage is stabilized.
        "use": False,  # uses the field plate in the experiment.
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
    "detect": {
        "mode": "abs",
        "abs": {
            "transition": "ac",
            "detunings": np.linspace(-3.5, 3.5, 35) * ureg.MHz,
            "on_time": 5 * ureg.us,
            "off_time": 1 * ureg.us,
            "delay": 8 * ureg.us,
            "amplitude": 17 * ureg.mV,
            "repeats": 512,
        },
    },
    "rf": {
        "channel_name": "rf_coil",
        "avg_center_frequency": 119.225 * ureg.MHz,
        "sweep": {
            "detuning_abar_to_bbar": -55 * ureg.kHz,
            "detuning_a_to_b": 55 * ureg.kHz,
            "amplitude": 0.3 * ureg.V,
            "T_0": 0.3 * ureg.ms,
            "T_e": 0.15 * ureg.ms,
            "T_ch": 25 * ureg.ms,
            "scan": 30 * ureg.kHz,
        },
        "rabi": {
            "detuning": 0 * ureg.kHz,
            "amplitude": 0.3 * ureg.mV,
            "duration": 1 * ureg.ms,
        },
    },
    "lf": {
        "channel_name": "rf_coil",
        "equilibrate": {
            "center_frequency": 140 * ureg.kHz,
            "Sigma": 0,
            "Zeeman_shift_along_b": 5 * ureg.kHz,
            "piov2_amplitude": 220 * ureg.mV,
            "piov2_duration": 15 * ureg.us,
            "use_composite": True,
            "composite_segments": 3,
        },
        "rabi": {
            "center_frequency": 140 * ureg.kHz,
            "Sigma": 0,  # 0, +1, -1.
            "Zeeman_shift_along_b": 5 * ureg.kHz,
            "detuning": 0 * ureg.kHz,
            "amplitude": 50 * ureg.mV,
            "duration": 1 * ureg.ms,
        },
        "ramsey": {
            "center_frequency": 140 * ureg.kHz,
            "Sigma": 0,  # 0, +1, -1.
            "Zeeman_shift_along_b": 5 * ureg.kHz,
            "detuning": 0 * ureg.kHz,
            "amplitude": 50 * ureg.mV,
            "piov2_time": 100 * ureg.us,
            "wait_time": 200 * ureg.us,
            "phase": 0,
        },
    },
}

def update_parameters_from_shared(parameters: dict, shared_parameters=None):
    """Recursively updates undefined parameters from shared parameters."""
    if shared_parameters is None:
        shared_parameters = deepcopy(_shared_parameters)
    parameters = deepcopy(parameters)
    for kk in shared_parameters:
        if kk in parameters:
            if isinstance(parameters[kk], dict):
                parameters[kk] = update_parameters_from_shared(
                    parameters[kk], shared_parameters[kk]
                )
        else:
            parameters[kk] = shared_parameters[kk]
    return parameters
