import numpy as np
import scipy.constants as c
from onix.units import ureg, Q_


class EuYSO:
    def __init__(self, x: Q_, y: Q_, z: Q_, concentation: float):
        self.volume = x * y * z
        self.concentration = concentation

        self._density = 4.44 * ureg.g / ureg.cm**3
        self._yso_atom_mass = (89 * 2 + 28 + 16 * 5) * ureg.Da

    @property
    def eu_site1_number_density(self) -> Q_:
        return (self._density / self._yso_atom_mass * self.concentration).to("mm^-3")

    @property
    def eu_site1_numbers(self) -> float:
        return (self.eu_site1_number_density * self.volume).to("").magnitude


def homogeneous_linewidth(T):
    """
    Konz 2003, Fig. 7. For site 1.
    """
    return 7.2e-3 * T**7 # Hz, with T in K


def lifetime(T):
    """
    Konz 2003, Fig. 9. For site 1.
    200 cm^-1 is used for the 7F0 - 7F1 splitting. This number may need to be modified.
    """
    A = 3.7e8
    B = 1.1e-10
    delta_E = 200 * 100 * c.c * c.h
    term1 = A / np.exp(delta_E / (c.k * T) - 1)
    term2 = B * T**7
    return 1 / (term1 + term2)
