import numpy as np
from astropy.timeseries import LombScargle
from scipy.interpolate import interp1d


def ls_psd_to_power_spectrum(LS_psd, N_time_series):
    """Converts from astropy Lomb-Scargle unnormalized PSD to power spectrum.

    See https://docs.astropy.org/en/stable/timeseries/lombscargle.html#psd-normalization-unnormalized.
    To convert from FFT to Lomb-Scargle unnormalized PSD, it is psd_LS = abs(y_fft[positive]) ** 2 / N,
    where y_fft is the np.fft.fft result, psd_LS is the Lomb-Scargle PSD,
    and N is the length of the time series.

    The astropy psd_LS is not the actual PSD. Actual PSD = psd_LS * 2 / sample_rate. Then the power spectrum
    is PSD * freq_resolution = psd_LS * 2 * freq_resolution / sample_rate = psd_LS * 2 / N.
    """
    return LS_psd * 2 / N_time_series


def frequency_sensitivity_from_experiment_times(timestamps_start, timestamps_end, frequencies, phases: int = 20):
    """Returns the sensitivities to oscillations at different frequencies for nonuniform experiment times.
    
    It assumes that the data is averaged in each experiment cycle.
    """
    cycle_durations = timestamps_end - timestamps_start
    powers = []
    for frequency in frequencies:
        spectral_power_for_this_frequency = []
        for phase in np.linspace(0, 2 * np.pi, phases, endpoint=False):
            simulated_signal = (
                np.cos(2 * np.pi * frequency * timestamps_start + phase) - np.cos(2 * np.pi * frequency * timestamps_end + phase)
            ) * np.sqrt(2) / (2 * np.pi * frequency * cycle_durations)
            ls = LombScargle((timestamps_start + timestamps_end) / 2, simulated_signal, normalization="psd")
            spectral_power_for_this_frequency.append(ls_psd_to_power_spectrum(ls.power(frequency), len(simulated_signal)))
        powers.append(np.average(spectral_power_for_this_frequency))
    return interp1d(frequencies, powers)
