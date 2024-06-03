import numpy as np
from onix.headers.quarto_filter import Quarto
from onix.analysis.fitter import Fitter
import time

def sine(x, A, omega, phi):
    return A * np.sin(omega*x + phi)

class PulseTubeTracker(Quarto):
    def __init__(self, address = '/dev/ttyACM3', num_periods = 10, get_data_time = 10e-3):
        """
        Class to monitor the noise of the Pulse Tube so that we may keep phase when we run experiments

        Parameters:
            - num_periods: how many past periods of the pulse tube we care about
            - get_data_time: how often to get new data from the quarto
        """

        super().__init__(address) # connect to the quarto

        self.adc_interval = 1e-6
        self.num_periods = num_periods # we only care about the last N periods of PT cycle
        self.buffer = np.zeros(int(10 * 0.8 / self.adc_interval)) # slight overestimation of how many points we will ever need to save
        self.samples_to_get = get_data_time / self.adc_interval # how many samples to ask the quarto for every time

        self.t_axis = np.arange(0, len(self.buffer) * self.adc_interval, self.adc_interval)
        self.time_fit = 0

        self.A = 0
        self.omega = 0
        self.phi = 0

        self.historical_A = np.zeros(self.num_periods)
        self.historical_omega = np.zeros(self.num_periods)
        self.historical_phi = np.zeros(self.num_periods)
        self.average_period = 0
        

    def _get_data(self): 
        """
        Get data from Quarto. Keep only the most recent data in self.buffer
        """
        data = self.data(self.samples_to_get)
        self.buffer = np.roll(self.buffer, -self.samples_to_get)
        self.buffer[-self.samples_to_get:] = data

    def _get_fit(self): # every average period we need to run this again
        """
        Fit data
        """
        fitter = Fitter(sine)

        fitter.set_data(self.t_axis, self.buffer)

        p0 = {
            "A": np.average(self.historical_A),
            "omega": np.average(self.historical_omega),
            "phi": np.average(self.historical_phi)
        }

        fitter.set_p0(p0)
        fitter.set_bounds("A", 0, np.inf) # otherwise we could fit a negative A and the phi would change

        fitter.fit()
        self.time_fit = time.time_ns()
        self.A = fitter.fitted_value("A")
        self.omega = fitter.fitted_value("omega")
        self.phi = fitter.fitted_value("phi")
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

        self.average_period = 2 * np.pi / np.mean(self.historical_omega)

    @property
    def phase(self):
        """
        Current phase, at the time of calling this function, using the most recent fit
        """
        time_since_last_fit = (time.time_ns() - self.time_fit) / (1e9) # time, in s, since the last fit was performed
        return (self.omega * time_since_last_fit + self.phi) % (2*np.pi)
    
    @property
    def period(self): # wait, approx. num_periods * 0.8 s at the start before doing the first fit. After this, the (n-1)th fit determines how long to wait before doing the nth
        """
        Average period over the last num_periods
        """
        return self.average_period
    
