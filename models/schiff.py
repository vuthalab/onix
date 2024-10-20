import numpy as np
import scipy.constants as _c

from onix.units import ureg, Q_, num_to_Q


class MeasurementSettings:
    """Settings to determine a frequency measurement's sensitivity.

    Args:
        SNR: signal to noise ratio per measurement, default 1.
        measurement_time: total measurement time in seconds, default 1 day.
        dead_time: dead time per measurement, default 30 ms.
        coherence_time: spin precession time, default 1 ms.
    """

    def __init__(
        self,
        SNR: float = 1.0,
        measurement_time: float | Q_ = 1 * ureg.day,
        down_time: float | Q_ = 30 * ureg.ms,
        coherence_time: float | Q_ = 1 * ureg.ms,
    ):
        self.SNR = SNR
        self.measurement_time = num_to_Q(measurement_time, ureg.s)
        self.down_time = num_to_Q(down_time, ureg.s)
        self.coherence_time = num_to_Q(coherence_time, ureg.s)

    @property
    def frequency_sensitivity(self) -> Q_:
        T_total = self.measurement_time
        T_down = self.down_time
        tau = self.coherence_time
        SNR = self.SNR
        prefactor = 2 * np.pi * tau * SNR

        denominator = prefactor * np.sqrt(T_total / (tau + T_down))

        return (1 / denominator).to("Hz")


class System:
    """A system including a Schiff-moment sensitivity nucleus.
    
    See Flambaum and Feldmeier https://doi.org/10.1103/PhysRevC.101.015502 for details.

    Args:
        K_S: nuclear Schiff moment sensitivity to theta_QCD. Default 1.
        K_Z: atomic EDM sensitivity factor. Default 1.
    """
    @classmethod
    def K_S_from_nuclear_constants(
        cls,
        J: float = 1/2,
        beta_2: float = 0.129,
        beta_3: float = 0.099,
        Z: float = 88,
        A: float = 225,
        E_doublet_keV: float = 55
    ) -> float:
        """Text below Eq. 13 of Flambaum and Feldmeier."""
        K_J = 3 * J / (J + 1)
        K_beta = 791 * beta_2 * beta_3 ** 2
        K_A = 0.00031 * Z * A ** (2/3)
        K_E = 55 / E_doublet_keV
        return K_J * K_beta * K_A * K_E

    @classmethod
    def K_Z_from_atom_number(cls, Z: float = 88, A: float = 225) -> float:
        """Eqs. 18 and 19 of Flambaum and Feldmeier.
        
        Question: Does this only work for neutral atoms or does it also work for charged ions?
        """
        def K(Z: float = 88, A: float = 225):
            a0 = _c.physical_constants["Bohr radius"][0]
            R = 1.2e-15 * A ** (1/3)
            gamma = np.sqrt(1 - (Z * _c.fine_structure) ** 2)
            return Z**2 * (a0 / (2 * Z * R)) ** (2 - 2 * gamma)
        return K(Z, A) / K()

    def __init__(self, K_S: float = 1.0, K_Z: float = 1.0):
        self.K_S = K_S
        self.K_Z = K_Z

    @property
    def Schiff_in_theta_QCD(self) -> Q_:
        """Eq. 14 of Flambaum and Feldmeier."""
        return self.K_S * ureg.e * ureg.fm**3

    @property
    def atomic_EDM_in_theta_QCD(self) -> Q_:
        """Eq. 20 of Flambaum and Feldmeier."""
        factor = -9e-17 * ureg.cm / ureg.fm**3
        return self.Schiff_in_theta_QCD * factor * self.K_Z

    @property
    def energy_shift_in_theta_QCD(self) -> Q_:
        raise NotImplementedError()

    @property
    def frequency_shift_in_theta_QCD(self) -> Q_:
        h = _c.h * ureg.J / ureg.Hz
        return (self.energy_shift_in_theta_QCD / h).to("Hz")


class Atom(System):
    """Atom sensitivity to theta QCD.
    
    See Flambaum and Feldmeier https://doi.org/10.1103/PhysRevC.101.015502 for details.
    Assumes that the applied electric field is aligned with the atom's quantization direction.

    Args:
        K_S: nuclear Schiff moment sensitivity to theta_QCD. Default 1.
        K_Z: atomic EDM sensitivity factor. Default 1.
        E_field: electric field applied to the atom to observe an energy shift. Default 1 MV/cm.
    """
    def __init__(
        self,
        K_S: float = 1.0,
        K_Z: float = 1.0,
        E_field: float | Q_ = 1 * ureg.MV / ureg.cm,
    ):
        super().__init__(K_S, K_Z)
        self.E_field = num_to_Q(E_field, ureg.V / ureg.m)

    @property
    def energy_shift_in_theta_QCD(self) -> Q_:
        return -self.atomic_EDM_in_theta_QCD * self.E_field


class Molecule(System):
    """Molecule sensitivity to theta QCD.
    
    See Flambaum and Feldmeier https://doi.org/10.1103/PhysRevC.101.015502 for details.
    Assumes that the nuclear spin is aligned perfectly with the internuclear axis.

    K_S: nuclear Schiff moment sensitivity to theta_QCD. Default 1.
    K_Z: atomic EDM sensitivity factor. Default 1.
    W_S: molecular enhancement factor in atomic units (e / (4 * pi * epsilon_0 * a0**4)).
        Default 50000.
    """
    def __init__(
        self,
        K_S: float = 1.0,
        K_Z: float = 1.0,
        W_S: float = 50000,
    ):
        super().__init__(K_S, K_Z)
        epsilon_0 = _c.epsilon_0 * ureg.F / ureg.m
        self.W_S = W_S * ureg.e / (4 * np.pi * epsilon_0 * ureg.a0**4)

    @property
    def energy_shift_in_theta_QCD(self) -> Q_:
        return self.W_S * self.Schiff_in_theta_QCD


class NewPhysicsSensitivities:
    """Sensivitity conversion between T-violation terms.

    Assumes contribution of only a single source.
    Assumes that the gpiNN sensitivities are the same as radium-225, which is
    probably a reasonable assumption for Schiff moment enhanced nuclei.
    """
    def __init__(self, theta_QCD: float = 1e-10):
        self.theta_QCD = theta_QCD

        # See https://doi.org/10.1103/PhysRevC.101.015502.
        self.a0 = -2.6
        self.a1 = 12.9
        self.a2 = -6.9
        
        self.gg0_in_theta_QCD = -0.37
        self.gg0_in_du_plus_dd = 0.8e15 / ureg.cm
        self.gg1_in_du_minus_dd = 4e15 / ureg.cm

    @property
    def gg0(self) -> float:
        return np.abs(self.theta_QCD * self.gg0_in_theta_QCD)

    @property
    def gg1(self) -> float:
        return np.abs(self.gg0 * self.a0 / self.a1)

    @property
    def gg2(self) -> float:
        return np.abs(self.gg1 * self.a0 / self.a2)

    @property
    def chromo_edm_difference(self) -> Q_:
        """\tilda{d}_u - \tilda{d}_d"""
        return self.gg1 / self.gg1_in_du_minus_dd

    @property
    def chromo_edm_sum(self) -> Q_:
        """\tilda{d}_u + \tilda{d}_d"""
        return self.gg0 / self.gg0_in_du_plus_dd

    @property
    def new_particle_mass(self) -> float:
        """1 loop level mass limits in TeV from quark chromo EDM limits.

        This function comes from email exchanges Andrew had with Jordy De Vries
        in Fall, 2021.  This allows one to connect hadronic TSV sensitivity
        to sensitivity to new particles through quark chromo EDM limits.

        For unit conversions hbar * c = 1 = 197 MeV fm

        So you can express an EDM limit like:
        10^-14 fm in units of inverse energy as
        10^-14 fm = 10^-14 fm/(hbar c) = 10^-14 fm/(197 MeV fm)
        = 10^-14/(197) MeV^-1
        """
        m_q = 5  # MeV - very approximate up quark mass

        prefactor = _c.fine_structure * m_q / np.pi

        d_q_fm = self.chromo_edm_difference.to("fm").magnitude

        fm_to_inv_MeV = 1 / 197
        d_q_inv_MeV = d_q_fm * fm_to_inv_MeV

        MeV_to_TeV = (1.0 / 1e-6) * (1e-12 / 1.0)

        return MeV_to_TeV * np.sqrt(prefactor * 1 / d_q_inv_MeV)

    @property
    def a0_over_fa(self) -> float:
        """Axion a_0 / f_a limit.
        
        This assumes that the the oscillation in theta_QCD has been constrained.
        a_0 is the axion field amplitude, and f_a is the coupling constant of axions
        and gluons. This is simply theta_QCD per definition of axions.

        See PRD 89, 043522 (2014) Section IV for details.
        In PRX 7, 041034 (2017), this quantity is C_G a_0 / f_a.
        """
        return self.theta_QCD

def inverse_fa_limit(frequency, theta_QCD_amplitude):
    """Limit on the axion gluon coupling constant from theta_QCD oscillation amplitude.
    
    See PRD 89, 043522 (2014) Section IV and PRX 7, 041034 (2017) for details.
    In PRX 7, 041034 (2017), the returned quantity is C_G / f_a.

    The local dark matter density is rho_DM = a_0^2 * m_a^2 / 2.
    m_a is the axion particle mass.
    The oscillation frequency is simply m_a (both mass and frequency in natural units).

    Consistency check:
        Neutron EDM experiment in PRD 92, 092003 (2015) constrains theta_QCD to ~1e-10.
        Their lowest measurement frequency is ~1e-9 Hz. Using the same dataset, they analyzed
        their maximum bound on C_G / f_a in PRX 7, 041034 (2017) to be 1e-21 GeV^-1.
        This function gives inverse_fa_limit(frequency=1e-9, theta_QCD_amplitude=1e-10) = 1.7e-22 GeV^-1
        which is approximately the same. The smaller limit may come from that their theta_QCD oscillation
        bound are not as good as the static theta_QCD bound.

    Args:
        frequency: float, theta_QCD oscillation measured at frequency in Hz.
        theta_QCD_amplitude: float, theta_QCD oscillation amplitude.

    Returns:
        float, constraint on 1 / f_a in GeV^-1.
    """
    GeV_to_J = _c.e * 1e9
    rho_DM = 0.4 * GeV_to_J * 100**3  # J/m^3, assumes axions saturate local dark matter density.
    energy_density_natural_to_SI = GeV_to_J**4 / (_c.hbar * _c.c)**3  # 1 GeV^4 to J/m^3
    rho_DM_natural = rho_DM / energy_density_natural_to_SI  # GeV^4
    frequency_natural_to_SI = GeV_to_J / _c.hbar  # 1 GeV to radians
    frequency_natural = frequency * 2 * np.pi / frequency_natural_to_SI  # GeV
    a0_over_fa = theta_QCD_amplitude  # this is simply the definition of axions.
    return a0_over_fa * frequency_natural / np.sqrt(2 * rho_DM_natural)


def axion_frequency_to_mass(frequency):
    """Hz to eV"""
    return 2 * np.pi * frequency * _c.hbar / _c.e


def axion_mass_to_frequency(mass):
    """eV to Hz"""
    return mass * _c.e / (2 * np.pi * _c.hbar)
