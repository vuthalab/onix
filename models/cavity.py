import numpy as _np
import scipy.constants as _c


def nBK7(lamda=780e-9):
    """Index of refraction of BK7 glass as function of wavelength

    From some random but pro looking website. Apparently from the Sellmeier equation.

    Args:
        lamda: float, wavelength in meters, default(lamda, 780e-9).
    """
    # For this equation we convert lamda to micrometers from meters
    lamda = 1e6 * lamda
    Term1numer = 1.03961212 * lamda**2.0
    Term1denom = lamda**2.0 - 0.00600069867
    Term1 = Term1numer / Term1denom
    Term2numer = 0.231792344 * lamda**2.0
    Term2denom = lamda**2.0 - 0.0200179144
    Term2 = Term2numer / Term2denom
    Term3numer = 1.01046945 * lamda**2.0
    Term3denom = lamda**2.0 - 103.560653
    Term3 = Term3numer / Term3denom
    n = _np.sqrt(1.0 + Term1 + Term2 + Term3)
    return n


def nFusedSilica(lamda=780e-9):
    """Index of refraction of fused silica glass as function of wavelength.

    From some random but pro looking website. Apparently from the Sellmeier equation.

    Args:
        lamda: float, wavelength in meters, default(lamda, 780e-9).
    """
    # For this equation we convert lamda to micrometers from meters
    lamda = 1e6 * lamda
    Term1numer = 0.6961663 * lamda**2.0
    Term1denom = lamda**2.0 - 0.0684043**2.0
    Term1 = Term1numer / Term1denom

    Term2numer = 0.4079426 * lamda**2.0
    Term2denom = lamda**2.0 - 0.1162414**2.0
    Term2 = Term2numer / Term2denom

    Term3numer = 0.8974794 * lamda**2.0
    Term3denom = lamda**2.0 - 9.896161**2.0
    Term3 = Term3numer / Term3denom

    n = _np.sqrt(1.0 + Term1 + Term2 + Term3)
    return n


class Mirror:
    """Mirror object.

    Radius of curvature taken as positive for concave mirrors.
    For convex mirror use negative radius of curvature.
    """

    version = "0.0"

    def __init__(self):
        self.material = "Fused Silica"
        self.radiusOfcurvature = 0.250  # meters
        self.radius = (12.7 / 2.0) * 1.0e-3  # meters
        self.lamda = 780e-9  # Design wavelength, meters

        # Thorlabs measurement
        # E03 coating intensity reflectivity
        # (measured at 8 degrees angle of incidence)
        RE03 = 0.9984334  # At 780 nm
        self._R = RE03

        # Thorlabs measurement
        # E03 coating intensity transmissivity (0 degree angle of incidence)
        TE03 = 0.000493
        self._T = TE03

        self.thickness = 6.35 * 1e-3  # meters

        # Description of mirror shape
        self.shape = "Spherical Concave"

    @property
    def curvature_len(self):
        ROC = self.radiusOfcurvature
        R = self.radius
        return _np.abs(ROC - _np.sqrt(ROC**2 + R**2))

    @property
    def n(self):
        """Index of refraction based on self.lamda wavelength."""
        if self.material == "Fused Silica":
            return nFusedSilica(self.lamda)
        elif self.material == "BK7":
            return nBK7(self.lamda)
        else:
            raise Exception("Substrate material index not defined")

    @property
    def R(self):
        """Intensity reflectivity."""
        return self._R

    @R.setter
    def R(self, value):
        """Checks if intensity reflectivity is between 0 and 1.

        Args:
            value: float, intensity reflectivity, value from 0 to 1.
        """
        if value < 0:
            raise ValueError("Negative value not allowed: %s" % value)
        if value + self.T > 1:
            raise ValueError("R+T can't be larger than 1: %s" % value)
        self._R = value

    @property
    def T(self):
        """Intensity transmissivity."""
        return self._T

    @T.setter
    def T(self, value):
        """Checks if intensity reflectivity is between 0 and 1.

        Args:
            value: float, intensity transmissivity, value from 0 to 1.
        """
        if value < 0:
            raise ValueError("Negative value not allowed: %s" % value)
        if value + self.R > 1:
            raise ValueError("R+T can't be larger than 1: %s" % value)
        self._T = value

    @property
    def loss(self):
        """Mirror Intensity loss."""
        return 1.0 - self.R - self.T


class Cavity:
    """Basic Fabry-Perot cavity.

    Properties derived from Kogelnik and Li, 1966.  See Fig. 5 for a quick
    reference on the beam parameter (E_0/e radius).

    Stability parameters and round trip Gouy phase shift from LIGO technical
    note LIGO-T1300189-v1.

    Kogelnik and Li, 1966 variable definitions:
        b: confocal parameter (confocal cavity when d=R=b).
        t: distance to true cavity waist from outer edge of mirror.
        d: distance between outer edges of cavity mirrors (cavity length).
        R: mirror radius of curvature (R_1 = R_2).
        R_1: mirror 1 radius of curvature.
        R_2: mirror 2 radius of curvature.
        w_0: beam waist, E_0/e beam radius (minimum spot size in the cavity).
        w_0_eff: beam waist as seen from the outside.

    LIGO technical note variables (using Kogelnik and Li definitions):
        g_1: 1 - d/R_1.
        g_2: 1 - d/R_2.

    Beam size definitions:
        "w": E_0/e radius,"beam radius" or "spot size".
        "2*w": "beam diameter".
        "2*w_0": minimum beam diameter, is the "beam waist".

    Args:
        length: float, the cavity spacer length in meters.
        lamda: cavity mirror high reflectivity coating.
        ROC: float, mirror radius of curvature in meters.
    """

    def __init__(self, mirror):
        """Mirror function.

        Args:
            mirror: Mirror instance.
        """
        self.mirror = mirror

        self.lamda = mirror.lamda
        self.ROC = mirror.radiusOfcurvature

        # Ideal cavity length for 2-photon transition cavity
        self.length = 0.073987

    @property
    def b(self):
        """Actual cavity confocal parameter as defined in Kogelnik and Li.

        See equation 52 of Kogelnik and Li, 1966

        This is the effective confocal parameter given as case 2 of
        Table II.
        """
        return _np.sqrt(self.length * (2.0 * self.ROC - self.length))

    @property
    def b_eff(self):
        """Returns effective confocal parameter.

        This is the effective confocal parameter given as case 4 of
        Table II, as would be seen from outside the cavity with the lensing
        effects of a diverging lens (i.e. the mirror substrate).
        """
        d = self.d
        n = self.mirror.n
        numer = self.ROC * _np.sqrt(d * (2.0 * self.ROC - d))
        denom = 2.0 * self.ROC + d * (n**2.0 - 1.0)
        return 2.0 * numer / denom

    @property
    def d(self):
        """'d' Cavity length from Kogelnik and Li.

        This is the distance from mirror outer edge to
        mirror outer edge.  See Table II, No 4.
        """
        mirror_extra = self.mirror.thickness - self.mirror.curvature_len
        return self.length + 2.0 * mirror_extra

    @property
    def finesse(self):
        """Finesse for a Fabry-Perot.

        Returns:
            Cavity finesse.
        """
        R = self.mirror.R
        numer = _np.pi * _np.sqrt(R)
        denom = 1.0 - R
        return numer / denom

    @property
    def fsr(self):
        """Free spectral range in Hz."""
        return _c.c / (2.0 * self.length)

    @property
    def linewidth(self):
        """Approximate linewidth from Finesse in the high reflectivity limit.

        Returns:
            Cavity linewidth in Hz.
        """
        return self.fsr / self.finesse

    @property
    def phi_RT(self):
        """Round trip phase shift in radians.

        4*pi*L/lamda.

        Returns:
            phi round trip, Radians.
        """
        numer = 4.0 * _np.pi * self.length
        denom = self.lamda
        return numer / denom

    @property
    def stable(self):
        """Determines if the cavity is stable.

        Equation 8 from Kogelnik and Li.

        Returns:.
            bool
        """
        stability_parameter = self._g_1 * self._g_2
        stable_cavity = True
        if stability_parameter > 1:
            stable_cavity = False
        if stability_parameter < 0:
            stable_cavity = False
        return stable_cavity

    @property
    def t(self):
        """Distance to the true cavity waist from the mirror.

        Case 2 of Table II in Kogelnik and Li.

        Returns:
            Distance to actual waist from the mirror.
        """
        d = self.d
        return d / 2.0

    @property
    def t_eff(self):
        """'t' distance to "effective" waist as defined in Kogelnik and Li.

        This is the distance from the outside edge of the back
        cavity mirror. Case 4 of Table II in Kogelnik and Li.

        Returns:
            Distance to effective waist from outer edge of back mirror.
        """
        d = self.d
        n = self.mirror.n
        numer = n * d * self.ROC
        denom = 2.0 * self.ROC + d * (n**2.0 - 1.0)
        return numer / denom

    @property
    def Q(self):
        """Quality Factor.

        2*L*F/lamda.

        Returns:
            float, Q.
        """
        numer = 2.0 * self.length * self.finesse
        denom = self.lamda
        return numer / denom

    @property
    def tau(self):
        """Ringdown time.

        Returns:
            Ringdown time in seconds.
        """
        numer = self.length * self.finesse
        denom = _np.pi * _c.c
        return numer / denom

    @property
    def transverse_mode_spacing(self):
        """The spacing in Hz between adjacent transverse modes.

        See equation 5 of the LIGO technical note.
        This is the spacing between TEM_00 and TEM_10, or TEM_43 and TEM_44.

        Returns:
            float, spacing in Hz.
        """
        return self.fsr * self._round_trip_Gouy_phase / (2.0 * _np.pi)

    @property
    def w_0(self):
        """Actual spot size inside the cavity, E_0/e beam radius.

        Beam spot size from confocal parameter Case 2 of Table II in Kogelnik
        and Li.

        Returns:
            Spot size in meters.
        """
        numer = self.lamda * self.b
        denom = 2.0 * _np.pi
        return _np.sqrt(numer / denom)

    @property
    def w_0_eff(self):
        """Effective spot size of the cavity, as seen from the outside.

        Again, this is the E_0/e beam radius value.

        Beam spot size from confocal parameter Case 4 of Table II in Kogelnik
        and Li.

        Returns:
            Spot size in meters.
        """
        numer = self.lamda * self.b_eff
        denom = 2.0 * _np.pi
        return _np.sqrt(numer / denom)

    @property
    def _g_1(self):
        """Cavity g-factor for mirror 1.

        Determines cavity stability.
        """
        return 1.0 - self.length / self.ROC

    @property
    def _g_2(self):
        """Cavity g-factor for mirror 2.

        The mirrors are identical for this class.

        Determines cavity stability.
        """
        return self._g_1

    @property
    def _round_trip_Gouy_phase(self):
        """The phase between transverse cavity eigenmodes.

        Used for calculating the transverse mode spacing of the cavity.

        See equation 4 of the LIGO technical note. g_1 sets the sign below.
        """
        argument = _np.sign(self._g_1) * _np.sqrt(self._g_1 * self._g_2)
        return 2.0 * _np.arccos(argument)

    def Gouy_Phase(self, m=0.0, n=0.0):
        """The Gouy phase shift in Radians of the TEM_m,n Hermite-Gauss mode.

        This is the phase shift incurred as a beam diverges from a waist.  So,
        for a single pass in the cavity the phase shift is twice the Gouy_Phase
        calculated here, and I think for the beam to be on resonance
        Gouy_Phase = pi/2 must be met.

        Args:
            m: float, needs to be an non-negative integer, default(1.).
            n: float, needs to be an non-negative integer, default(1.).

        Returns:
            float, from 0 to 2*pi.
        """
        prefactor = m + n + 1.0
        numer = self.lamda * 0.5 * self.length
        denom = _np.pi * self.w_0**2.0
        return prefactor * _np.arctan(numer / denom)


class PlanoConcaveCavity(Cavity):
    """Optical cavity where one mirror is concave and the other plano.

    See Table II, No 1 from Kogelnik and Li, 1966.
    """

    def __init__(self, mirror):
        super(PlanoConcaveCavity, self).__init__(mirror)
        self.length = 0.100  # quad cavity length is 100 mm

    @property
    def d(self):
        mirror_extra = self.mirror.thickness - self.mirror.curvature_len
        return self.length + mirror_extra

    @property
    def b(self):
        """See Table II, No.1 of Kogelnik and Li."""
        return 2.0 * _np.sqrt(self.length * (self.ROC - self.length))

    @property
    def b_eff(self):
        """Rayleigh range of the effective beam seen through the plano-concave mirror.

        magnification_ratio_square comes from the Lens Equation for Gaussian
        beams and the focal length formula for a thin lens.
        """
        d = self.d
        n = self.mirror.n
        r = self.mirror.radiusOfcurvature
        magnification_ratio_square = r / (d * (n**2 - 1) + r)
        return self.b * magnification_ratio_square

    @property
    def t(self):
        """Distance to the true waist to the plano-concave lens side of the cavity."""
        return self.d

    @property
    def t_eff(self):
        """Distance of the effective beam waist to the plano-concave lens side of the cavity.

        The effective beam is the beam measured from the
        plano-concave side of the cavity to couple effectively into the cavity.
        Positive values means the effective beam waist is after the plano-concave mirror.

        This formula is derived using Table II, No.1 of Kogelnik and Li,
        Lens Equation for Gaussian beam, and focal length formula for thin lens.
        """
        d = self.d
        n = self.mirror.n
        r = self.mirror.radiusOfcurvature
        numer = d * n * r
        denom = r + d * (n**2 - 1)
        return numer / denom

    @property
    def _g_2(self):
        """Flat mirror, 1 - d/ROC_2 = 1"""
        return 1.0
