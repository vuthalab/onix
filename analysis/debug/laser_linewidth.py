from typing import Optional
import numpy as np


class LaserLinewidth:
    """Calculates laser linewidth.

    Assumes that the laser frequency error is proportional to the error signal.

    Args:
        error_signals: 2D list or np.array of floats. Multiple traces of laser error signals.
        time_resolution: float, error signal time resolution in s.
        discriminator_slope: float, error signal slope in V/Hz.
        max_points_per_decade: int or None. If int, it averages points if the points are denser than
            the set value.

    Properties:
        f: np.array, frequency axis for Fourier-transformed data.
        W_V: np.array, voltage noise power spectrum.
        W_nu: np.array, laser frequency noise power spectrum.
        W_phi: np.array, laser phase noise power spectrum.
        linewidth: float, measured laser linewidth in Hz.
    """
    def __init__(
            self,
            error_signals,
            time_resolution: float,
            discriminator_slope: float,
            max_points_per_decade: Optional[int] = None,
        ):
        self._error_signals = error_signals
        self._time_resolution = time_resolution
        self._duration = time_resolution * len(error_signals[0])
        self._discriminator_slope = discriminator_slope
        self._max_points_per_decade = max_points_per_decade
        self._get_voltage_noise_spectrum()
        self._get_frequency_and_phase_noise_spectra()
        self._get_phase_noise_integral()

    def _get_binned_variable(self, variable):
        if self._max_points_per_decade is None or self._frequency_start_bin_index is None:
            return variable
        else:
            first_part = variable[:self._frequency_start_bin_index]
            second_part = [[] for kk in self._bin_edges]
            for kk in range(self._frequency_start_bin_index, len(variable)):
                digitized_kk = self._digitized[kk]
                second_part[digitized_kk].append(variable[kk])
            second_part = [kk for kk in second_part if len(kk) > 0]
            second_part = [np.average(kk) for kk in second_part]
            return np.append(first_part, second_part)

    @property
    def f(self):
        return self._get_binned_variable(self._f)

    @property
    def W_V(self):
        return self._get_binned_variable(self._W_V)

    @property
    def W_nu(self):
        return self._get_binned_variable(self._W_nu)

    @property
    def W_phi(self):
        return self._get_binned_variable(self._W_phi)

    @property
    def W_phi_integral(self):
        return self._get_binned_variable(self._W_phi_integral)

    def _get_voltage_noise_spectrum(self):
        frequencies = np.fft.fftfreq(len(self._error_signals[0]), self._time_resolution)
        fft_mask = frequencies > 0
        self._f = frequencies[fft_mask]
        if self._max_points_per_decade is not None:
            log10_max = np.log10(max(self._f) * 1.0001)
            log10_min = np.log10(min(self._f))
            bin_edge_num = int((log10_max - log10_min) * self._max_points_per_decade) + 1
            self._bin_edges = np.logspace(log10_min, log10_max, bin_edge_num)
            self._digitized = np.digitize(self._f, self._bin_edges)

            old_number = None
            self._frequency_start_bin_index = None
            for kk, number in enumerate(self._digitized):
                if number == old_number:
                    self._frequency_start_bin_index = kk - 1
                    break
                old_number = number
        self._W_V = np.zeros(len(self._f))
        for voltages in self._error_signals:
            V_T = voltages / np.sqrt(self._duration)
            V_f = np.fft.fft(V_T) * self._time_resolution
            W_V = np.abs(V_f) ** 2
            self._W_V += 2 * W_V[fft_mask]
        self._W_V /= len(self._error_signals)

    def _get_frequency_and_phase_noise_spectra(self):
        self._W_nu = self._W_V / self._discriminator_slope ** 2
        self._W_phi = self._W_nu / self._f ** 2

    def _get_phase_noise_integral(self):
        frequency_resolution = self._f[1] - self._f[0]
        # integrating from the highest frequency.
        self._W_phi_integral = np.cumsum(self._W_phi[::-1] * frequency_resolution)[::-1]
        self.linewidth = self._f[np.argmin(self._W_phi_integral > 1 / np.pi)]
