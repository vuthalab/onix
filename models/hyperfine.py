from numbers import Number

import numpy as np
import qutip
from onix.units import ureg

USE_EU151 = False


def rotation_matrix(alpha, beta, gamma):
    """Rotation matrix.

    alpha, beta, and gamma are Euler angles in degrees.
    """
    def rot_z(theta):
        a = np.radians(theta)
        c = np.cos(a)
        s = np.sin(a)
        return np.array([[c,s,0],[-s,c,0],[0,0,1]])

    def rot_y(theta):
        b = np.radians(theta)
        c = np.cos(b)
        s = np.sin(b)
        return np.array([[c,0,-s],[0,1,0],[s,0,c]])

    return np.matmul(rot_z(gamma), np.matmul(rot_y(beta), rot_z(alpha)))


def rotate(operator, alpha, beta, gamma):
    rot = rotation_matrix(alpha, beta, gamma)
    return np.matmul(rot, np.matmul(operator, np.transpose(rot)))


def quadrupole_tensor_own_frame(D, E):
    return np.array([[-E, 0, 0], [0, E, 0], [0, 0, D]])


def Zeeman_tensor_own_frame(g_1, g_2, g_3):
    return np.array([[g_1, 0, 0], [0, g_2, 0], [0, 0, g_3]])


class HyperfineStates:
    """Hyperfine and Zeeman states of Eu:YSO 7F0 or 5D0 electronic state.

    All inputs and outputs are in the dielectric frame (D1, D2, b).

    Args:
        state_labels: list of strs, labels of Zeeman states in increasing energies.
        quadrupole_tensor: The electric quadrupole tensor in the dielectric frame in 2π MHz.
        Zeeman_tensor: The quadrupole Zeeman tensor in the dielectric frame in 2π MHz / T.
        B_field: list of floats or float, magnetic field in the dielectric frame in T.
            If float, it specifies the magnetic field on the D1 axis. The magnetic field on
            the D2 and b axes is set to zero.
    """
    def __init__(self, state_labels, quadrupole_tensor, Zeeman_tensor, B_field):
        self.I = 5/2
        self.states = state_labels
        self._I_x = qutip.jmat(self.I, "x")
        self._I_y = qutip.jmat(self.I, "y")
        self._I_z = qutip.jmat(self.I, "z")
        self._mu_N = 7.6225932188  # MHz / T
        self._I_axes = [self._I_x, self._I_y, self._I_z]
        self._quadrupole_tensor = quadrupole_tensor
        self._Zeeman_tensor = Zeeman_tensor
        self._Hamiltonian: qutip.Qobj = self.H_total(B_field)

    def H_quadrupole(self):
        H_q = 0
        for kk in range(3):
            for ll in range(3):
                H_q += self._I_axes[kk] * self._quadrupole_tensor[kk][ll] * self._I_axes[ll]
        return H_q

    def H_Zeeman(self, B_field):
        if isinstance(B_field, Number):
            B_field = [B_field, 0, 0]
        H_Z = 0
        for kk in range(3):
            for ll in range(3):
                H_Z += self._I_axes[kk] * self._Zeeman_tensor[kk][ll] * B_field[ll]
        return H_Z

    def H_total(self, B_field):
        return self.H_quadrupole() + self.H_Zeeman(B_field)

    def energies_and_eigenstates(self):
        return self._Hamiltonian.eigenstates()

    @property
    def _mu_x(self):
        return -(self._Zeeman_tensor[0][0] * self._I_x + self._Zeeman_tensor[0][1] * self._I_y + self._Zeeman_tensor[0][2] * self._I_z) / self._mu_N

    @property
    def _mu_y(self):
        return -(self._Zeeman_tensor[1][0] * self._I_x + self._Zeeman_tensor[1][1] * self._I_y + self._Zeeman_tensor[1][2] * self._I_z) / self._mu_N

    @property
    def _mu_z(self):
        return -(self._Zeeman_tensor[2][0] * self._I_x + self._Zeeman_tensor[2][1] * self._I_y + self._Zeeman_tensor[2][2] * self._I_z) / self._mu_N

    def mu_Ix(self, eigenvector: qutip.Qobj):
        return np.abs((eigenvector.dag() * self._mu_x * eigenvector))

    def mu_Iy(self, eigenvector: qutip.Qobj):
        return np.abs((eigenvector.dag() * self._mu_y * eigenvector))

    def mu_Iz(self, eigenvector: qutip.Qobj):
        return np.abs((eigenvector.dag() * self._mu_z * eigenvector))

    def m_Ix(self, eigenvector: qutip.Qobj):
        return np.abs((eigenvector.dag() * self._I_x * eigenvector))

    def m_Iy(self, eigenvector: qutip.Qobj):
        return np.abs((eigenvector.dag() * self._I_y * eigenvector))

    def m_Iz(self, eigenvector: qutip.Qobj):
        return np.abs((eigenvector.dag() * self._I_z * eigenvector))

    def magnetic_field_sensitivity(self, eigenvector: qutip.Qobj):
        """Magnetic field sensitivity on (D1, D2, b) axes in MHz / T."""
        return np.array(
            [self.mu_Ix(eigenvector), self.mu_Iy(eigenvector), self.mu_Iz(eigenvector)]
        ) * self._mu_N

    def Schiff_moment_sensitivity(self, eigenvector: qutip.Qobj):
        """Returns the dot product of nuclear spin and the electric field direction.

        Assumes that the electric field is on the D1 axis.
        """
        return self.m_Ix(eigenvector)

    def m1_elements(self):
        """Magnetic dipole transition matrix elements between different Zeeman levels.

        Returns:
            (m1_plus, m1_minus, m1_zero)
            m1_plus: Dict[str, Dict[str, complex]], M1 matrix elements for sigma+ polarization.
            m1_minus: Dict[str, Dict[str, complex]], M1 matrix elements for sigma- polarization.
            m1_zero: Dict[str, Dict[str, complex]], M1 matrix elements for pi polarization.

            The first key is the initial state label, and the second key is the final state label.
            The unit is 2π MHz / T.
        """
        # transformation into spherical tensor basis
        sph_tensor_transform = np.array(
            [
                [-1 / np.sqrt(2), 1j / np.sqrt(2), 0],
                [1 / np.sqrt(2), 1j / np.sqrt(2), 0],
                [0, 0, 1],
            ]
        ) # +1, -1, 0 basis
        Zeeman_sph = np.matmul(
            sph_tensor_transform,
            np.matmul(
                self._Zeeman_tensor,
                np.matrix.getH(sph_tensor_transform)
            )
        )

        # +1 spherical tensor component of the nuclear spin vector; *not* the raising operator
        I_plus = -self._I_x / np.sqrt(2) + 1j * self._I_y / np.sqrt(2)
        I_minus = self._I_x / np.sqrt(2) + 1j * self._I_y / np.sqrt(2)
        I_zero = self._I_z
        I_bases = [I_plus, I_minus, I_zero]

        M1_plus = 0
        M1_minus = 0
        M1_zero = 0
        for kk in range(3):
            M1_plus += Zeeman_sph[0][kk] * I_bases[kk]
            M1_minus += Zeeman_sph[1][kk] * I_bases[kk]
            M1_zero += Zeeman_sph[2][kk] * I_bases[kk]

        elements_plus = {}
        elements_minus = {}
        elements_zero = {}
        energys, eigenstates = self.energies_and_eigenstates()
        for kk, state_a in enumerate(eigenstates):
            elements_plus[self.states[kk]] = {}
            elements_minus[self.states[kk]] = {}
            elements_zero[self.states[kk]] = {}
            for ll, state_b in enumerate(eigenstates):
                elements_plus[self.states[kk]][self.states[ll]] = (
                    state_b.dag() * M1_plus * state_a
                ).tr()
                elements_minus[self.states[kk]][self.states[ll]] = (
                    state_b.dag() * M1_minus * state_a
                ).tr()
                elements_zero[self.states[kk]][self.states[ll]] = (
                    state_b.dag() * M1_zero * state_a
                ).tr()
        return (elements_plus, elements_minus, elements_zero)

# 153Eu3+:YSO
energies = {
    "7F0": {
        "a": 0 * ureg.MHz,
        "b": 119.2 * ureg.MHz,  # Yano1992, Lauritzen2012
        "c": 209.25 * ureg.MHz,  # Yano1992, Lauritzen2012 209.2 MHz. Our spectroscopy gives 209.25.
    },
    "5D0": {
        "a": 450.8 * ureg.MHz,  # Yano1992, Lauritzen2012
        "b": 191.3 * ureg.MHz,  # Yano1992, Lauritzen2012
        "c": 0 * ureg.MHz,
    }
}


# Cruzeiro2018, for YSO, relative to lab frame.
dielectric_angles = {
    "alpha": -140,
    "beta": 172,
    "gamma": -51,
}


# Cruzeiro2018, for 151Eu3+:YSO, relative to lab frame.
quadrupole_angles = {
    "7F0": {
        "alpha": -29.9,
        "beta": 53.4,
        "gamma": 124.05,
    },
    "5D0": {
        "alpha": 165.3,
        "beta": 154.91,
        "gamma": 107.81,
    },
}


# Yano1991 and Yano1992. Sign comes from Cruzeiro2018.
if not USE_EU151:
    quadrupole_tensor_magnitudes_MHz = {
        "7F0": {
            "D": -32.0,
            "E": -32.0 * 0.674 / 3,
        },
        "5D0": {
            "D": 69.7,
            "E": 69.7 * 0.660 / 3,
        },
    }
else:
    quadrupole_tensor_magnitudes_MHz = {
        "7F0": {
            "D": -12.4,
            "E": -12.4 * 0.661 / 3,
        },
        "5D0": {
            "D": 27.3,
            "E": 27.3 * 0.644 / 3,
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


# Cruzeiro2018, for 151Eu3+:YSO.
Zeeman_angles = {
    "7F0": {
        "alpha": 105.25,
        "beta": 163.74,
        "gamma": 124.56,
    },
    "5D0": {
        "alpha": 70.53,
        "beta": 5.0,
        "gamma": 62.17,
    },
}

if USE_EU151:
    _mu_ratio = 1
else:
    _mu_ratio = 1.5324 / 3.4718 # https://www-nds.iaea.org/relnsd/vcharthtml/VChartHTML.html
# Cruzeiro2018, for 151Eu3+:YSO, scaled by the 153 / 151 nuclear magnetic dipole moment.
Zeeman_tensor_magnitudes_MHz_per_T = {
    "7F0": {
        "g_1": 4.3 * _mu_ratio,
        "g_2": 5.559 * _mu_ratio,
        "g_3": -10.891 * _mu_ratio,
    },
    "5D0": {
        "g_1": 9.11 * _mu_ratio,
        "g_2": 9.158 * _mu_ratio,
        "g_3": 9.069 * _mu_ratio,
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
