import numpy as _np
import scipy.constants as _c


class LaserField:
    """Model for Gaussian beams.

    Extracts parameters such as peak intensity from a known beam waist and laser power.

    When modifying this class it is important that beam sizes are defined
    with respect to w_0.  So apply changes through getters and setters via
    w_0.

    Laser intensity defined by (up to a prefactor): exp(-2*x**2/w_0**2)

    Attributes:
        electric_field_max: Laser's electric field maximum (found at the waist) [V/m].
        frequency: laser frequency [Hz].
        intensity_peak: Peak laser intensity (found at the waist) [W/m**2].
        k: wavenumber in [m**-1].
        omega: laser frequency in angular units [s**-1].
        rayleigh_range: distance from the waist to where the beam size doubles [m].
            From Brooker's optics book.

    Args:
        lamda: float, wavelength [m], default(780 nm).
        w_0: float, 1/e^2 intensity radius [m], default(100 um).
        P: float, laser power [W], default(1 mW).
    """

    def __init__(self, lamda=780.0e-9, w_0=100e-6, P=1e-3):
        self.lamda = lamda
        self.w_0 = w_0
        self.P = P

    @property
    def frequency(self):
        return _c.c / self.lamda

    @property
    def omega(self):
        return 2.0 * _np.pi * self.frequency

    @property
    def k(self):
        return 2.0 * _np.pi / self.lamda

    @property
    def rayleigh_range(self):
        return self.w_0**2.0 * _np.pi / self.lamda

    def intensity(self, z=0.0, r=0.0):
        """Returns the intensity of the laser field.

        Intensity of the laser field is a function of the radial, r, and
        longitudinal coordinate, z.

        Args:
            z: float, longitudinal position in meters, default(0.).
            r: float, radial position in meters, default(0.).

        Returns
            float, laser intensity in W/m**2.
        """
        return gaussian_intensity(z=z, r=r, w_0=self.w_0, P0=self.P, lamda=self.lamda)

    def electric_field(self, z=0.0, r=0.0):
        """Returns electric field as a function of the radial, r, and longitudinal coordinate, z.

        Args:
            z: a float, longitudinal position in meters.
            r: a float, radial position in meters.

        Returns:
            A float, electric field in V/m.
        """
        return self._electric_field_from_intensity(intensity=self.intensity(z, r))

    @property
    def intensity_peak(self):
        return 2 * self.P / (_np.pi * self.w_0**2.0)

    @property
    def electric_field_max(self):
        return self._electric_field_from_intensity(intensity=self.intensity_peak)

    def set_ten_ninety_values(self, ten_um, ninety_um):
        """Sets the beam waist.

        Set the beam waist based on the measured 10% and 90% power measurements.
        This assumes you are at the beam waist. This is a measurement utility function.

        Args:
            ten_um: float, 10% power measurement distance in micrometers.
            ninety_um: float, 90% power measurement distance in micrometers.

        Returns:
            float, 1/e^2 intensity diameter in micrometers.
        """
        diameter_um = _np.abs(ninety_um - ten_um)
        um = 1e-6
        diameter = um * diameter_um
        self.w_0 = 0.5 * diameter / 0.64
        return 2.0 * self.w_0 / um

    @property
    def ten_ninety_diameter(self):
        """Returns the 10/90 diameter of the beam in um"""
        um = 1e-6
        return 2.0 * 0.64 * self.w_0 / um

    def _electric_field_from_intensity(self, intensity):
        """Electric field amplitude [V/m] for a given intensity [W/m**2].

        |E| = sqrt(2 * I/ (c*epsilon_0))

        Assuming vacuum (n=1)
        """
        prefactor = 2.0 / (_c.c * _c.epsilon_0)
        return _np.sqrt(prefactor * intensity)

    def set_beam_waist_from_intensity(self, intensity):
        """Calculates beam waist by the light intensity at the center of the beam waist.

        Args:
            intensity: float, intensity at the center of the beam waist in W/m**2.
        """
        self.w_0 = _np.sqrt(2 * self.P / (intensity * _np.pi))


def gaussian_intensity(z=0.0, r=0.0, w_0=100.0e-6, P0=1.0, lamda=780.0e-9):
    """Returns the time averaged intensity (W/m**2) of a laser (pulsed or CW).

    Time averaged intensity is function of the radial position (this is an approximation),
    the axial position from the beam waist, and the beam waist.

    Args:
        z: axial position from the waist, meters.
        r: radial position, meters.
        w_0: minimum beam spot size, the 1/e^2 intensity value, meters.
        P0: time averaged laser power, watts.
        lamda: laser wavelength, meters.
    """
    # Beam spot size at position z
    wE = gaussian_beam_waist(z=z, w_0=w_0, lamda=lamda)
    I0_z = 2 * P0 / (_np.pi * wE**2.0)  # Intensity at z=z, r=0
    # Intensity reduction by distance r from the peak intensity
    I_rz = I0_z * _np.exp(-2 * r**2.0 / wE**2.0)

    return I_rz


def gaussian_beam_waist(z=0.0, w_0=100.0e-6, lamda=780e-9):
    """Returns the spot size at a distance 'z' from the beam waist.

    See Kogelnik1966 Eq. 20. The beam waist is the spot size at z=0.
    Both beam waist and spot size are beam radius values.

    Args:
        z: axial position from the beam waist, meters.
        w_0: beam waist, the 1/e^2 intensity value, meters.
        lamda: laser wavelength, meters.
    """
    numer = lamda * z
    denom = _np.pi * w_0**2.0
    Term = (numer / denom) ** 2.0

    wE = _np.sqrt(w_0**2.0 * (1.0 + Term))

    return wE


def power_through_aperture(aperture_radius, spot_size):
    """The fraction of light transmitted by a circular aperture.

    Units just need to be the same between the aperture_radius and
    the spot_size for the function to work.

    The spot size (w(z)) of a beam a distance z from the the beam waist (w_0, the
    minimum 1/e E-field radius) is

    w(z) = w_0 * sqrt(1 + (z/z_R)**2)

    where z_R is the Rayleigh range, defined as

    z_R = pi * w_0**2/lambda

    (in vacuum where n=1)

    Args:
        aperture_radius: float, radius.
        spot_size: float, the 1/e electric field radius.

    Returns:
        float, fraction of light transmitted.
    """
    r = aperture_radius
    w = spot_size
    return 1 - _np.exp(-2 * r**2 / w**2)

