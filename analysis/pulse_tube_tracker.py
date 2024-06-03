import numpy as np
from onix.headers.quarto_filter import Quarto
from onix.analysis.fitter import Fitter
import time

def sine(x, A, omega, phi):
    return A * np.sin(omega*x + phi)

class PulseTubeTracker(Quarto):
    def __init__(self, address = '/dev/ttyACM3'):
        super().__init__(address) # connect to the quarto

        self.adc_interval = 1e-6
        self.num_periods = 10 # we only care about the last N periods of PT cycle
        self.buffer = np.zeros(int(10 * 0.8 / self.adc_interval)) # slight overestimation of how many points we will ever need to save
        self.samples_to_get = 2 # how many samples to ask the quarto for every time

        self.t_axis = np.arange(0, len(self.buffer) * self.adc_interval, self.adc_interval)
        self.time_fit = 0
        self.omega = 0
        self.phi = 0

    def _get_data(self):
        data = self.device.data(self.samples_to_get)
        self.buffer = np.roll(self.buffer, -self.samples_to_get)
        self.buffer[-self.samples_to_get:] = data

    def _get_fit(self):
        fitter = Fitter(sine)

        fitter.set_data(self.t_axis, self.buffer)
        fitter.set_p0()
        fitter.set_bounds("A", 0, np.inf) # otherwise we could fit a negative A and the phi would change

        fitter.fit()
        self.time_fit = time.time_ns()
        self.omega = fitter.fitted_value("omega")
        self.phi = fitter.fitted_value("phi")

    @property
    def phase(self):
        time_since_last_fit = (time.time_ns() - self.time_fit) / (1e9) # time, in s, since the last fit was performed
        return self.omega * time_since_last_fit + self.phi