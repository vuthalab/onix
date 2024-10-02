from typing import Optional
import numpy as np
from onix.analysis.power_spectrum import PowerSpectrum, _get_binned_variable

    
class LaserLinewidth(PowerSpectrum):
    """Calculates laser linewidth.

    Assumes that the laser frequency error is proportional to the error signal.

    Args:
        num_samples: int, number of samples per trace
        time_resolution: float, error signal time resolution in s.
        discriminator_slope: float, error signal slope in V/Hz.
        max_points_per_decade: int or None. If int, it averages points if the points are denser than
            the set value.

    Properties:
        f: np.array, frequency axis for Fourier-transformed data.
        num_of_averages: int, number of traces calculated
        error_signal_average: float, average of all voltages across all traces
        voltage_spectrum: ndarray, voltage noise spectrum
        relative_voltage_spectrum: ndarray, voltage noise spectrum divided by average voltage
        power_spectrum: ndarray, power noise spectrum
        relative_power_spectrum: ndarray, power noise spectrum divided by average voltage squared
        W_V: np.array, voltage noise power spectrum.
        W_nu: np.array, laser frequency noise power spectrum.
        W_phi: np.array, laser phase noise power spectrum.
        linewidth: float, measured laser linewidth in Hz.
    """
    def __init__(
            self,
            num_samples: int,
            time_resolution: float,
            discriminator_slope: float,
            max_points_per_decade: Optional[int] = None,
        ):
        super().__init__(num_samples, time_resolution, max_points_per_decade)
        self._discrimator_slope = discriminator_slope

    @property
    def W_nu(self):
        self._get_frequency_and_phase_noise_spectra()
        if self._max_points_per_decade == None:
            return self._W_nu
        else:
            return _get_binned_variable(self._max_points_per_decade, self._frequency_start_bin_index, self._bin_edges, self._digitized, self._W_nu)

    @property
    def W_phi(self):
        self._get_frequency_and_phase_noise_spectra()
        if self._max_points_per_decade == None:
            return self._W_phi
        else:
            return _get_binned_variable(self._max_points_per_decade, self._frequency_start_bin_index, self._bin_edges, self._digitized, self._W_phi)

    @property
    def W_phi_integral(self):
        _W_phi_integral, linewidth = self._get_phase_noise_integral()
        if self._max_points_per_decade == None:
            return _W_phi_integral
        else:
            return _get_binned_variable(self._max_points_per_decade, self._frequency_start_bin_index, self._bin_edges, self._digitized, _W_phi_integral)
    
    @property
    def linewidth(self):
        W_phi_integral, linewidth = self._get_phase_noise_integral()
        return linewidth

    def _get_frequency_and_phase_noise_spectra(self):
        unbinned_power_spectrum = np.mean(self._power_spectrums, axis=0)
        self._W_nu = unbinned_power_spectrum / self._discrimator_slope ** 2 
        self._W_phi = self._W_nu / self._frequencies ** 2

    def _get_phase_noise_integral(self):
        self._get_frequency_and_phase_noise_spectra()
        frequency_resolution = self._frequencies[1] - self._frequencies[0]
        # integrating from the highest frequency.
        _W_phi_integral = np.cumsum(self._W_phi[::-1] * frequency_resolution)[::-1]
        linewidth = self._frequencies[np.argmin(_W_phi_integral > 1 / np.pi)]
        return _W_phi_integral, linewidth