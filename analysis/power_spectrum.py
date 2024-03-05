import numpy as np

class PowerSpectrum:
    """
    Calculates the power spectrum of a voltage signal.

    Args:
        num_of_samples: int, number of samples per trace
        time_resolution: float, error signal time resolution in s.
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
    """
    def __init__(self, num_of_samples: int, time_resolution: float, max_points_per_decade: int = None):
        self._num_of_samples = num_of_samples
        self._time_resolution = time_resolution
        self._max_points_per_decade = max_points_per_decade
        self._duration = time_resolution * self._num_of_samples
        self._frequencies = self._calculate_frequencies()
        self._error_signal_avgs = []
        self._power_spectrums = []
        self._last_updated_index = -1
        self._get_bin_start()

    def _get_bin_start(self):
        if self._max_points_per_decade is not None:
            log10_max = np.log10(max(self._frequencies) * 1.0001)
            log10_min = np.log10(min(self._frequencies))
            bin_edge_num = int((log10_max - log10_min) * self._max_points_per_decade) + 1
            self._bin_edges = np.logspace(log10_min, log10_max, bin_edge_num)
            self._digitized = np.digitize(self._frequencies, self._bin_edges)

            old_number = None
            self._frequency_start_bin_index = None
            for kk, number in enumerate(self._digitized):
                if number == old_number:
                    self._frequency_start_bin_index = kk - 1
                    break
                old_number = number
        else:
            self._frequency_start_bin_index = None

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
        W_V = 2 * W_V_calculated[self.fft_mask] 
        return W_V 

    @property
    def f(self):
        return self._get_binned_variable(self._frequencies)

    @property
    def num_of_averages(self):
        return len(self._error_signal_avgs)

    @property
    def error_signal_average(self):
        return np.average(self._error_signal_avgs)
    
    @property
    def power_spectrum(self):
        return self._get_binned_variable(np.mean(self._power_spectrums, axis=0))
    
    @property
    def relative_power_spectrum(self):
        return self.power_spectrum / self.error_signal_average ** 2

    @property
    def voltage_spectrum(self):
        return np.sqrt(self.power_spectrum)
    
    @property
    def relative_voltage_spectrum(self):
        return self.voltage_spectrum / np.abs(self.error_signal_average)


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
        W_V = 2 * W_V_calculated[self.fft_mask] 
        return W_V 

    @property
    def f(self):
        return self.frequencies

    @property
    def num_of_averages(self):
        return len(self._error_signal_1_avgs)

    @property
    def error_signal_1_average(self):
        return np.average(self._error_signal_1_avgs)
    
    @property
    def error_signal_2_average(self):
        return np.average(self._error_signal_2_avgs)

    @property
    def voltage_spectrum(self):
        return np.sqrt(np.mean(self._power_spectrums, axis=0))
    
    @property
    def relative_voltage_spectrum(self):
        return self.voltage_spectrum / np.sqrt(self.error_signal_1_average * self.error_signal_2_average)
    
    @property
    def power_spectrum(self):
        return np.mean(self._power_spectrums, axis=0)
    
    @property
    def relative_power_spectrum(self):
        return self.power_spectrum / (self.error_signal_1_average * self.error_signal_2_average)

