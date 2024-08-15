from astropy.timeseries import LombScargle


def psd_to_power_spectrum(psd, N_time_series):
    """Converts from astropy Lomb-Scargle unnormalized PSD to power spectrum.

    See https://docs.astropy.org/en/stable/timeseries/lombscargle.html#psd-normalization-unnormalized.
    To convert from FFT to Lomb-Scargle unnormalized PSD, it is psd_LS = abs(y_fft[positive]) ** 2 / N,
    where y_fft is the np.fft.fft result, psd_LS is the Lomb-Scargle PSD,
    and N is the length of the time series.
    
    Therefore, to convert from Lomb-Scargle unnormalized PSD to power spectrum, it should be
    power_spectrum = psd_LS * 2 * N 
    """
    return psd * 2 / N_time_series


def 
