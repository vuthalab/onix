import numpy as np


class LaserLinewidth:
    """Calculates laser linewidth.

    Assumes that the laser frequency error is proportional to the error signal.

    Args:
        error_signals: 2D list or np.array of floats. Multiple traces of laser error signals.
        time_resolution: float, error signal time resolution in s.
        discriminator_slope: foat, error signal slope in V/Hz.

    Attributes:
        f: np.array, frequency axis for Fourier-transformed data.
        W_V: np.array, voltage noise power spectrum.
        W_nu: np.array, laser frequency noise power spectrum.
        W_phi: np.array, laser phase noise power spectrum.
        linewidth: float, measured laser linewidth in Hz.
    """
    def __init__(self, error_signals, time_resolution: float, discriminator_slope: float):
        self._error_signals = error_signals
        self._time_resolution = time_resolution
        self._duration = time_resolution * len(error_signals[0])
        self._discriminator_slope = discriminator_slope
        self._get_voltage_noise_spectrum()
        self._get_frequency_and_phase_noise_spectra()
        self._get_phase_noise_integral()

    def _get_voltage_noise_spectrum(self):
        frequencies = np.fft.fftfreq(len(self._error_signals[0]), self._time_resolution)
        fft_mask = frequencies > 0
        self.f = frequencies[fft_mask]
        self.W_V = np.zeros(len(self.f))
        for voltages in self._error_signals:
            V_T = voltages / np.sqrt(self._duration)
            V_f = np.fft.fft(V_T) * self._time_resolution
            W_V = np.abs(V_f) ** 2
            self.W_V += 2 * W_V[fft_mask]
        self.W_V /= len(self._error_signals)

    def _get_frequency_and_phase_noise_spectra(self):
        self.W_nu = self.W_V / self._discriminator_slope ** 2
        self.W_phi = self.W_nu / self.f ** 2

    def _get_phase_noise_integral(self):
        frequency_resolution = self.f[1] - self.f[0]
        # integrating from the highest frequency.
        self.W_phi_integral = np.cumsum(self.W_phi[::-1] * frequency_resolution)[::-1]
        self.linewidth = self.f[np.argmin(self.W_phi_integral > 1 / np.pi)]
