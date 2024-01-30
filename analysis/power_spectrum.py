import numpy as np

class PowerSpectrum:
    """
    Calculates the power spectrum of the laser.
    Args:
        error_signals: 2D list or np.array of floats. Multiple traces of laser error signals.
        time_resolution: float, error signal time resolution in s.

    Properties:
        f: np.array, frequency axis for Fourier-transformed data.
        W_V: np.array, voltage noise power spectrum.
    """
    def __init__(self, error_signals, time_resolution: float): # when you initialize you want it to automatically get the power spectrum of the data you've given in
        self._error_signals = error_signals
        self._time_resolution = time_resolution
        self._duration = time_resolution * len(error_signals[0])
        self.frequencies = self._calculate_frequencies(error_signals[0]) 
        self.power_spectrums = []
        self._power_spectrum(error_signals)
        self.kk = 0 # iterate over this variable to tell which element to overwrite when using rolling averages

    def _calculate_frequencies(self, voltage_trace): 
        """
        Calculates the frequencies at which we will find the power. As the length of each trace and time resolution is constant, this is constant. 
        """
        frequencies = np.fft.fftfreq(len(voltage_trace), self._time_resolution) # the frequency ouput of this always starts with 0
        self.fft_mask = frequencies > 0
        f = frequencies[self.fft_mask]
        return f

    def _single_power_spectrum(self, voltage_trace): 
        """
        Calculate the power spectrum of one trace worth of data.
        """
        V_T = voltage_trace / np.sqrt(self._duration)
        V_f = np.fft.fft(V_T) * self._time_resolution
        W_V_calculated = np.abs(V_f) ** 2
        W_V = np.zeros(len(self.frequencies))
        W_V += 2 * W_V_calculated[self.fft_mask] # will this mask even work with the current setup
        self.dc_offset = W_V_calculated[0] # find the DC component of our power spectrum for later use in normalization, alternatively find the peak for the minimal frequency
        return W_V 
    
    def _power_spectrum(self, voltages_list): 
        """
        Calculate the averaged power spectrum of many traces of data.
        """
        for i in voltages_list:
            W_V = self._single_power_spectrum(i)
            self.power_spectrums.append(W_V)

    def update_data(self, voltage_trace):
        """
        Used for rolling averages. Calculates power spectrum of a new trace, overwrite one past trace, and calcualtes the new average.
        """
        W_V = self._single_power_spectrum(voltage_trace)
        self.power_spectrums[self.kk] = W_V

        if self.kk < len(self._error_signals):
            self.kk += 1
        else: 
            self.kk = 0

    def add_data(self, voltage_trace):
         W_V = self._single_power_spectrum(voltage_trace)
         self.power_spectrums.append(W_V)

    @property
    def f(self):
        return self.frequencies
    
    @property
    def power_spectrum(self):
        return np.mean(self.power_spectrums, axis = 0)
    
    @property
    def relative_power_spectrum(self):
        return (1*self.dc_offset) * np.mean(self.power_spectrums, axis = 0)

