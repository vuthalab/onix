import numpy as np

class PowerSpectrum:
    """
    Calculates the power spectrum of the laser.
    Args:
        num_of_samples: int, number of samples per trace
        time_resolution: float, error signal time resolution in s.

    Properties:
        f: np.array, frequency axis for Fourier-transformed data.
        num_of_averages: int, number of traces calculated
        error_signal_average: float, average of all voltages across all traces
        voltage_spectrum: ndarray, voltage noise spectrum
        relative_voltage_spectrum: ndarray, voltage noise spectrum divided by average voltage
        power_spectrum: ndarray, power noise spectrum
        relative_power_spectrum: ndarray, power noise spectrum divided by average voltage squared
    """
    def __init__(self, num_of_samples: int, time_resolution: float):
        self._num_of_samples = num_of_samples
        self._time_resolution = time_resolution
        self._duration = time_resolution * self._num_of_samples
        self.frequencies = self._calculate_frequencies()
        self._error_signal_avgs = []
        self._power_spectrums = []
        self._last_updated_index = -1

    def add_data(self, error_signal):
        self._power_spectrums.append(self._voltages_to_power_spectrum(error_signal))
        self._error_signal_avgs.append(np.average(error_signal))

    def update_data(self, error_signal):
        index_to_update = self._last_updated_index + 1
        if index_to_update == len(self._error_signal_avgs):
            index_to_update = 0
        self._power_spectrums[index_to_update] = self._voltages_to_power_spectrum(error_signal)
        self._error_signal_avgs[index_to_update] = np.average(error_signal)
        self._last_updated_index = index_to_update

    def _calculate_frequencies(self): 
        """
        Calculates the frequencies at which we will find the spectrum. 
        """
        frequencies = np.fft.fftfreq(self._num_of_samples, self._time_resolution) 
        self.fft_mask = frequencies > 0
        f = frequencies[self.fft_mask]
        return f

    def _voltages_to_power_spectrum(self, voltage_trace): 
        """
        Calculate the power spectrum of one trace worth of data.
        """
        V_T = voltage_trace / np.sqrt(self._duration)
        V_f = np.fft.fft(V_T) * self._time_resolution
        W_V_calculated = np.abs(V_f) ** 2
        W_V = np.zeros(len(self.frequencies))
        W_V += 2 * W_V_calculated[self.fft_mask] 
        return W_V 

    @property
    def f(self):
        return self.frequencies

    @property
    def num_of_averages(self):
        return len(self._error_signal_avgs)

    @property
    def error_signal_average(self):
        return np.average(self._error_signal_avgs)

    @property
    def voltage_spectrum(self):
        return np.sqrt(np.mean(self._power_spectrums, axis=0))
    
    @property
    def relative_voltage_spectrum(self):
        return self.voltage_spectrum / np.abs(self.error_signal_average)
    
    @property
    def power_spectrum(self):
        return np.mean(self._power_spectrums, axis=0)
    
    @property
    def relative_power_spectrum(self):
        return self.power_spectrum / self.error_signal_average ** 2


class CCedPowerSpectrum:
    def __init__(self, num_of_samples: int, time_resolution: float):
        self._num_of_samples = num_of_samples
        self._time_resolution = time_resolution
        self._duration = time_resolution * self._num_of_samples
        self.frequencies = self._calculate_frequencies()
        self._error_signal_1_avgs = []
        self._error_signal_2_avgs = []
        self._power_spectrums = []
        self._last_updated_index = -1

    def add_data(self, error_signal_1, error_signal_2):
        self._power_spectrums.append(self._voltages_to_power_spectrum(error_signal_1, error_signal_2))
        self._error_signal_1_avgs.append(np.average(error_signal_1))
        self._error_signal_2_avgs.append(np.average(error_signal_2))

    def update_data(self, error_signal_1, error_signal_2):
        index_to_update = self._last_updated_index + 1
        if index_to_update == len(self._error_signal_avgs):
            index_to_update = 0
        self._power_spectrums[index_to_update] = self._voltages_to_power_spectrum(error_signal_1, error_signal_2)
        self._error_signal_1_avgs[index_to_update] = np.average(error_signal_1)
        self._error_signal_2_avgs[index_to_update] = np.average(error_signal_2)
        self._last_updated_index = index_to_update

    def _calculate_frequencies(self): 
        """
        Calculates the frequencies at which we will find the spectrum. 
        """
        frequencies = np.fft.fftfreq(self._num_of_samples, self._time_resolution) 
        self.fft_mask = frequencies > 0
        f = frequencies[self.fft_mask]
        return f

    def _voltages_to_power_spectrum(self, voltage_trace_1, voltage_trace_2): 
        """
        Calculate the power spectrum of one trace worth of data.
        """
        V_T_1 = voltage_trace_1 / np.sqrt(self._duration)
        V_T_2 = voltage_trace_2 / np.sqrt(self._duration)
        V_f_1 = np.fft.fft(V_T_1) * self._time_resolution
        V_f_2 = np.fft.fft(V_T_2) * self._time_resolution
        W_V_calculated = np.conjugate(V_f_1) * V_f_2
        W_V = np.zeros(len(self.frequencies), dtype=complex)
        W_V += 2 * W_V_calculated[self.fft_mask] 
        return W_V 

    @property
    def f(self):
        return self.frequencies

    @property
    def num_of_averages(self):
        return len(self._error_signal_avgs)

    @property
    def error_signal_average(self):
        return np.average(self._error_signal_avgs)

    @property
    def voltage_spectrum(self):
        return np.sqrt(np.mean(self._power_spectrums, axis=0))
    
    @property
    def relative_voltage_spectrum(self):
        return self.voltage_spectrum / np.abs(self.error_signal_average)
    
    @property
    def power_spectrum(self):
        return np.mean(self._power_spectrums, axis=0)
    
    @property
    def relative_power_spectrum(self):
        return self.power_spectrum / self.error_signal_average ** 2

