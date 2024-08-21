import numpy as np
from onix.units import ureg

from onix.models.hyperfine import rotate, quadrupole_tensor_own_frame, Zeeman_tensor_own_frame, HyperfineStates


# 153EuCl3:6H2O. Ahlefeldt, Journal of Luminescence 143, 193 (2013)
energies = {
    "7F0": {
        "a": 0 * ureg.MHz,
        "b": 74.58 * ureg.MHz,
        "c": 144.65 * ureg.MHz,
    },
    "5D0": {
        "a": 246.9 * ureg.MHz,
        "b": 109.9 * ureg.MHz,
        "c": 0 * ureg.MHz,
    }
}


# These numbers are for Eu:YSO. They are likely incorrect.
dielectric_angles = {
    "alpha": -140,
    "beta": 172,
    "gamma": -51,
}


quadrupole_angles = {
    "7F0": {
        "alpha": 0,
        "beta": 6.2,
        "gamma": 87.07,
    },
    "5D0": {
        "alpha": 0,
        "beta": 6.2,
        "gamma": -13.22,
    },
}


# Martin, Journal of Luminescence 78, 19 (1998). These numbers give the correct hyperfine splittings.
quadrupole_tensor_magnitudes_MHz = {
    "7F0": {
        "D": -20.887,
        "E": -20.887 * 0.9245 / 3,
    },
    "5D0": {
        "D": 37.22,
        "E": 37.22 * 0.7415 / 3,
    },
}


quadrupole_tensor_D = {
    "7F0": rotate(
        rotate(
            quadrupole_tensor_own_frame(**quadrupole_tensor_magnitudes_MHz["7F0"]),
            **quadrupole_angles["7F0"],
        ),
        **dielectric_angles,
    ),
    "5D0": rotate(
        rotate(
            quadrupole_tensor_own_frame(**quadrupole_tensor_magnitudes_MHz["5D0"]),
            **quadrupole_angles["5D0"],
        ),
        **dielectric_angles,
    ),
}


Zeeman_angles = {
    "7F0": {
        "alpha": 0,
        "beta": 6.2,
        "gamma": 67.31,
    },
    "5D0": {
        "alpha": 0,
        "beta": 6.2,
        "gamma": -3.1,
    },
}


Zeeman_tensor_magnitudes_MHz_per_T = {
    "7F0": {
        "g_1": -0.673,
        "g_2": 1.794,
        "g_3": 1.359,
    },
    "5D0": {
        "g_1": 4.269,
        "g_2": 4.105,
        "g_3": 4.428,
    },
}


Zeeman_tensor_D = {
    "7F0": rotate(
        rotate(
            Zeeman_tensor_own_frame(**Zeeman_tensor_magnitudes_MHz_per_T["7F0"]),
            **Zeeman_angles["7F0"],
        ),
        **dielectric_angles,
    ),
    "5D0": rotate(
        rotate(
            Zeeman_tensor_own_frame(**Zeeman_tensor_magnitudes_MHz_per_T["5D0"]),
            **Zeeman_angles["5D0"],
        ),
        **dielectric_angles,
    ),
}


# Hyperfine and Zeeman states
small_B_field = 1e-5
# The Zeeman state labels for both electronic states.
state_labels = {
    "7F0": ["a", "a'", "b", "b'", "c", "c'"],
    "5D0": ["c", "c'", "b", "b'", "a", "a'"],
}
states = {
    "7F0": HyperfineStates(
        state_labels["7F0"],
        quadrupole_tensor_D["7F0"],
        Zeeman_tensor_D["7F0"],
        small_B_field,
    ),
    "5D0": HyperfineStates(
        state_labels["5D0"],
        quadrupole_tensor_D["5D0"],
        Zeeman_tensor_D["5D0"],
        small_B_field,
    ),
}

def get_optical_hyperfine_probabilities(B_field):
    states_7F0 = HyperfineStates(
        state_labels["7F0"],
        quadrupole_tensor_D["7F0"],
        Zeeman_tensor_D["7F0"],
        B_field,
    )

    states_5D0 = HyperfineStates(
        state_labels["5D0"],
        quadrupole_tensor_D["5D0"],
        Zeeman_tensor_D["5D0"],
        B_field,
    )

    optical_hyperfine_probabilities = {}
    g_energies, g_states = states_7F0.energies_and_eigenstates()
    e_energies, e_states = states_5D0.energies_and_eigenstates()
    for kk, g_label in enumerate(state_labels["7F0"]):
        optical_hyperfine_probabilities[g_label] = {}
        for ll, e_label in enumerate(state_labels["5D0"]):
            optical_hyperfine_probabilities[g_label][e_label] = np.abs(
                g_states[kk].overlap(e_states[ll]) * e_states[ll].overlap(g_states[kk])
            )
    
    return optical_hyperfine_probabilities
