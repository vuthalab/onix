import numpy as np
from onix.headers.microphone import Quarto, DEFAULT_GET_DATA_LENGTH
from onix.headers.find_quarto import find_quarto
from onix.analysis.fitter import Fitter
from onix.analysis.power_spectrum import PowerSpectrum
import time

def sine(x, A, omega, phi):
    return A * np.sin(omega*x + phi)

# fit to the last 10 periods, store the last 100 periods

class Microphone(Quarto, Fitter, PowerSpectrum):
    def __init__(self, address = find_quarto("digitizer"), num_periods_fit = 10, num_periods_save = 100, get_data_time = "Max"):
        """
        Class to monitor the noise of the Pulse Tube so that we may keep phase when we run experiments

        Parameters:
            - num_periods_fit: how many past periods of the pulse tube we should fit to
            - num_periods_save: how many of the past fitted periods we should save, for determinatin of experiment repetition rate
            - get_data_time: how often to get new data from the quarto
        """
         
        Quarto.__init__(self, address)
        Fitter.__init__(self, sine)       
        
        max_get_data_time = DEFAULT_GET_DATA_LENGTH * self.adc_interval

        if get_data_time == "Max":
            get_data_time = max_get_data_time
        elif get_data_time > max_get_data_time:
            get_data_time = max_get_data_time
            print(f"get_data_time is too large. Setting to maximal {max_get_data_time} s")

        self.get_data_time = get_data_time
        self.num_periods_fit = num_periods_fit # we only care about the last num_periods_fit of PT cycle
        self.num_periods_save = num_periods_save
        
        self.buffer = np.zeros(int(num_periods_fit * 0.8 / self.adc_interval)) # slight overestimation of how many points we will need to save) 
        self.samples_to_get = int(self.get_data_time / self.adc_interval) # how many samples to ask the quarto for every time

        self.t_axis = np.linspace(0,len(self.buffer) * self.adc_interval,len(self.buffer))
        self.time_fit = 0

        self.A = 0
        self.omega = 0
        self.phi = 0

        self.historical_A = np.zeros(self.num_periods_save)
        self.historical_omega = np.zeros(self.num_periods_save)
        self.historical_phi = np.zeros(self.num_periods_save)
        self.average_period = 0

        self.moving_avg = []

        #PowerSpectrum.__init__(self, num_of_samples=self.samples_to_get, time_resolution=self.adc_interval)
        PowerSpectrum.__init__(self, num_of_samples=len(self.buffer), time_resolution=self.adc_interval)

    def get_data(self): 
        """
        Get data from Quarto. Keep only the most recent data in self.buffer

        """
        data = self.data(self.samples_to_get)
        if self.samples_to_get <= len(self.buffer):
            self.buffer = np.roll(self.buffer, -self.samples_to_get)
            self.buffer[-self.samples_to_get:] = data
        else:
            self.buffer = data[-len(self.buffer):]

        #get data, compute FFT, take only the 1.4 Hz, and IFFT this
        #self.add_data(self.buffer)  

    def fill_buffer(self):
        for i in range(len(self.buffer) // self.samples_to_get):
            self.get_data()
        
        self.add_data(self.buffer)
        #print(self._power_spectrums) # the list of amplitudes from our power spectrum
        #lower_freq_index = np.argwhere(self.f>1).min() # locate where self.f hits 1 Hz
        #higher_freq_index = np.argwhere(self.f<10).max()# locate where self.f hits 10 Hz
        #lower_freq_index = 0
        #higher_freq_index = len(self.f)
        #print(lower_freq_index, higher_freq_index)
        #filtered_power_spectrum = self._power_spectrums[-1][lower_freq_index : higher_freq_index]
        #filtered_power_spectrum = np.sqrt(self._power_spectrums[-1])
        #print(filtered_power_spectrum)
        #self.inverse_fft = np.abs(np.fft.ifft(filtered_power_spectrum))


    def check_vals(self):
        print(np.isinf(self.t_axis), np.isnan(self.t_axis), np.isinf(self.buffer), np.isnan(self.buffer))

    def get_fit(self): # every average period we need to run this again
        """
        Fit data
        """
        self.set_data(self.t_axis, self.buffer)

        # TODO: if it is the first time we fit, there should be some manually given p0. After this we can use average of most recent fits
        # also possible that the initial fit will still work with guesses of zero
        p0 = {
            "A": 0.3, # np.average(self.historical_A),
            "omega": 2*np.pi, #np.average(self.historical_omega),
            "phi": 0 # np.average(self.historical_phi)
        }

        self.set_p0(p0)
        self.set_bounds("A", 0, np.inf) # otherwise we could fit a negative A and the phi would change
        self.set_bounds("omega", 0, np.inf)
        self.set_bounds("phi", 0, 2*np.pi)

        self.fit()
        self.time_fit = time.time_ns()
        self.A = self.results["A"]
        self.omega = self.results["omega"]
        self.phi = self.results["phi"]
        self._update_history()

    def _update_history(self):
        """
        Add new fitted params to rolling list
        """
        self.historical_A = np.roll(self.historical_A, -1)
        self.historical_phi = np.roll(self.historical_phi, -1)
        self.historical_omega = np.roll(self.historical_omega, -1)

        self.historical_A[-1] = self.A
        self.historical_phi[-1] = self.phi
        self.historical_omega[-1] = self.omega

        if np.mean(self.historical_omega) != 0: # if zero is not in this list at all
            self.average_period = 2 * np.pi / np.mean(self.historical_omega)
        else:
            self.average_period = 0

    def windowed_average(self, N):
        """# old code
        stack = np.array([ np.roll(self.buffer,s) for s in range(N)])
        stack_avg = np.average(stack,axis=0)
        self.avg = stack_avg
        """

        avgs = np.zeros_like(self.buffer)
        for i in range(self.buffer.size):
            avgs[i] = np.mean(self.buffer[max(i-N, 0):i+1])

        self.moving_avg = avgs


    @property
    def phase(self):
        """
        Current phase, at the time of calling this function, using the most recent fit
        """
        # TODO: should this be the most recently fitted phase, or the average phase? Probably most recently fitted
        time_since_last_fit = (time.time_ns() - self.time_fit) / (1e9) # time, in s, since the last fit was performed
        return (self.omega * time_since_last_fit + self.phi) % (2*np.pi)
    
    @property
    def period(self): # wait, approx. num_periods_save * 0.8 s at the start before doing the first fit. After this, the (n-1)th fit determines how long to wait before doing the nth
        """
        Average period over however many fits we have. If we have no fits, or all fitted omegas are zero, this returns None. 
        """
        not_enough_data_yet = np.isin(0, self.historical_omega)
        if not_enough_data_yet == False: 
            return self.average_period
        else:
            if np.zeros(len(self.historical_omega)) == self.historical_omega:
                return None
            else:
                return np.mean(self.historical_omega[self.historical_omega != 0])
    