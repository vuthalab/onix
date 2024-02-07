from functools import partial
import serial
import time
import re
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import animation
from onix.analysis.power_spectrum import PowerSpectrum


DEFAULT_GET_DATA_LENGTH = 50000

class Quarto:
    def __init__(self, location='/dev/ttyACM1'):
        self.address = location
        self.device = serial.Serial(self.address,
                                    baudrate=115200,
                                    timeout=0.2)

        sample_time_us = float(self._get_param("adc_interval")) 
        self.sample_time = sample_time_us * 1e-6
        self.sample_rate = 1/self.sample_time
        
    def _get_param(self, param):
        self.device.reset_input_buffer()
        self.device.reset_output_buffer()
        out = param + '\n'
        self.device.write(out.encode('utf-8'))
        response = self.device.readlines()
        response = response[0].decode('utf-8').strip('\n').split(" ")[-1]
        return response

    def _set_param(self, param, val):
        self.device.reset_input_buffer()
        self.device.reset_output_buffer()
        out = param + " " + str(val) + '\n'
        self.state = val
        self.device.write(out.encode('utf-8'))
        response = self.device.readlines()
        response = response[0].decode('utf-8').strip('\n').split(" ")[-1]
        return response
    
    def get_p_gain(self):
        val = float(self._get_param("p_gain"))    
        self.p_gain = val
        return val

    def get_i_time(self):
        val = float(self._get_param("i_time"))
        self.i_time = val
        return val

    def get_d_time(self):
        val = float(self._get_param("d_time"))
        self.d_time = val
        return val
    
    def get_integral_limit(self):
        val = float(self._get_param("integral_limit"))
        self.integral_limit = val
        return val

    def get_error_offset(self):
        val = float(self._get_param("error_offset"))
        self.error_offset = val
        return val

    def get_output_offset(self):
        val = float(self._get_param("output_offset"))
        self.output_offset = val
        return val

    def get_output_lower_limit(self):
        val = float(self._get_param("output_lower_limit"))
        self.output_lower_limit = val
        return val

    def get_output_uppper_limit(self):
        val = float(self._get_param("output_upper_limit"))
        self.output_upper_limit = val
        return val

    def get_pid_state(self):
        val = int(self._get_param("pid_state"))
        self.pid_state = val
        return val
    
    def get_integral(self):
        val = float(self._get_param("integral"))
        self.integral = val
        return val

    def set_p_gain(self, val):
        val = float(self._set_param("p_gain", val)) 
        self.p_gain = val
        return val   

    def set_i_time(self, val):
        val = float(self._set_param("i_time", val))
        self.i_time = val
        return val

    def set_d_time(self, val):
        val = float(self._set_param("d_time", val))
        self.d_time = val
        return val
    
    def set_integral_limit(self, val):
        val = float(self._set_param("integral_limit", val))
        self.integral_limit = val
        return val

    def set_error_offset(self, val):
        val = float(self._set_param("error_offset", val))
        self.error_offset = val
        return val

    def set_output_offset(self, val):
        val = float(self._set_param("output_offset", val))
        self.output_offset = val
        return val

    def set_output_lower_limit(self, val):
        val = float(self._set_param("output_lower_limit", val))
        self.output_lower_limit = val
        return val

    def set_output_upper_limit(self, val):
        val = float(self._set_param("output_upper_limit", val))
        self.output_upper_limit = val
        return val

    def set_pid_state(self, val):
        val = int(self._set_param("pid_state", val))
        self.pid_state = val
        return val
    
    def output_limit_indicator(self):
        """
        Prints warnings of if integrator and output are near their limits (within 10%) or outside of their limits.
        """
        val = int(self._get_param("limit_warnings"))
    
        if (val // 2**0) % 2 == 1:
            print("Integral warning")
        elif (val // 2**1) % 2 == 1:
            print("Integral out of bounds")
        else:
            print("Integrator good")
        
        if (val // 2**2) % 2 == 1:
            print("Output warning")
        elif (val // 2**3) % 2 == 1:
            print("Output out of bounds")
        else:
            print("Output good")
        
    def get_error_data(self, val = None):
        """
        Returns list of error data
        """
        if val is None:
            val = DEFAULT_GET_DATA_LENGTH
        self.error_data = []
        self.device.reset_input_buffer()
        self.device.reset_output_buffer()
        out = "error_data " + str(val) + "\n"
        self.device.write(out.encode('utf-8'))
        for i in range(val): 
            try:
                self.error_data.append(float(self.device.readline().decode('utf-8').strip('\n')))
            except ValueError as e:
                print(i)
                raise e
        self.error_data = np.asarray(self.error_data)

        return self.error_data
    
    def get_output_data(self, val = None):
        """
        Returns list of output data
        """
        if val is None:
            val = DEFAULT_GET_DATA_LENGTH
        self.output_data = []
        self.device.reset_input_buffer()
        self.device.reset_output_buffer()
        out = "output_data " + str(val) + "\n"
        self.device.write(out.encode('utf-8'))
        for i in range(val): 
            try:
                self.output_data.append(float(self.device.readline().decode('utf-8').strip('\n')))
            except ValueError as e:
                print(i)
                raise e
        self.output_data = np.asarray(self.output_data)

        return self.output_data

    def plot_error_data(self):
        """
        Plots one trace of error data
        """
        data = self.get_error_data()
        ts = np.arange(0,len(data))
        ts = ts*self.sample_time

        plt.plot(ts, a)
        plt.xlabel("time [s]")
        plt.ylabel("error voltage [V]")
        plt.show()

    def plot_output_data(self):
        """
        Plots one trace of output data
        """
        data = self.get_output_data()
        ts = np.arange(0,len(data))
        ts = ts*self.sample_time

        plt.plot(ts, a)
        plt.xlabel("time [s]")
        plt.ylabel("output voltage [V]")
        plt.show()

    def _calculate_spectrum(self, repeats = 10):
        """
        Calculates the voltage and power spectrums, both the un-normalized and relative.
        """
        noise = PowerSpectrum(DEFAULT_GET_DATA_LENGTH, self.sample_time)
        for i in range(repeats):
            noise.add_data(self.get_error_data())
            time.sleep(0.2)

        self.f = noise.f
        self.voltage_spectrum = noise.voltage_spectrum
        self.relative_voltage_spectrum = noise.relative_voltage_spectrum
        self.power_spectrum = noise.power_spectrum
        self.relative_power_spectrum = noise.relative_power_spectrum

    def plot_voltage_noise(self, repeats = 10):
        """
        Plot voltage noise spectrum using repeats number of averages
        """
        self._calculate_spectrum(repeats)
        plt.plot(self.f, self.voltage_spectrum)
        plt.xscale("log")
        plt.yscale("log")
        plt.xlabel("Frequency (Hz)")
        plt.ylabel("Voltage noise density (V/$\\sqrt{\\mathrm{Hz}}$)")
        plt.tight_layout()
        plt.show()

    def plot_relative_voltage_noise(self, repeats = 10):
        """
        Plot relative voltage noise spectrum using repeats number of averages
        """
        self._calculate_spectrum(repeats)
        plt.plot(self.f, self.relative_voltage_spectrum)
        plt.xscale("log")
        plt.yscale("log")
        plt.xlabel("Frequency (Hz)")
        plt.ylabel("Relative voltage noise density $\\sqrt{\\mathrm{Hz}}^{-1}$")
        plt.tight_layout()
        plt.show()

    def plot_power_noise(self, repeats = 10):
        """
        Plot power noise spectrum using repeats number of averages
        """
        self._calculate_spectrum(repeats)
        plt.plot(self.f, self.power_spectrum)
        plt.xscale("log")
        plt.yscale("log")
        plt.xlabel("Frequency (Hz)")
        plt.ylabel("Power noise density ($V^2/ \\mathrm{Hz}$)")
        plt.tight_layout()
        plt.show()

    def plot_relative_power_noise(self, repeats = 10):
        """
        Plot relative power noise spectrum using repeats number of averages
        """
        self._calculate_spectrum(repeats)
        plt.plot(self.f, self.relative_power_spectrum)
        plt.xscale("log")
        plt.yscale("log")
        plt.xlabel("Frequency (Hz)")
        plt.ylabel("Relative power noise density $\\mathrm{Hz}^{-1}$")
        plt.tight_layout()
        plt.show()

    def animated_error_data(self): # would be better to have these update, not refresh
        """
        Creates refreshing plot of error data
        """
        fig = plt.figure()

        self.get_error_data()
        t = np.linspace(0,len(self.error_data), len(self.error_data))
        t = t * self.sample_time

        self.axe = plt.axes()
        self.line, = self.axe.plot(t, self.error_data)
        plt.xlabel("time [s]")
        plt.ylabel("error voltage [V]")

        ani = animation.FuncAnimation(fig=fig, func=self._worker_animate_error, frames = 10, interval=10, blit=False)
        plt.show()

    def _worker_animate_error(self, frame):
        """
        Updates frames when animating error data
        """
        self.get_error_data()
        t = np.linspace(0,len(self.error_data), len(self.error_data))
        t = t * self.sample_time
        self.line.set_data(t, self.error_data)
        self.axe.set_ylim(min(self.error_data-0.001),max(self.error_data)+0.001)
        return self.error_data

    def animated_output_data(self): # would be better to have these update, not refresh
        """
        Creates refreshing plot of output data
        """
        fig = plt.figure()

        self.get_output_data()
        t = np.linspace(0,len(self.output_data), len(self.output_data))
        t = t*self.sample_time

        self.axe = plt.axes()
        self.axe.set_ylim(min(self.output_data)-0.01,max(self.output_data)+0.01)

        self.line, = self.axe.plot(t, self.output_data)
        plt.xlabel("time [s]")
        plt.ylabel("output voltage [V]")

        ani = animation.FuncAnimation(fig=fig, func=self._worker_animate_output, interval = 10, blit=False)

        plt.show()

    def _worker_animate_output(self, frame):
        """
        Updates frames when animating output data
        """
        self.get_output_data()
        t = np.linspace(0,len(self.output_data), len(self.output_data))
        t = t*self.sample_time
        self.line.set_data(t, self.output_data)
        self.axe.set_ylim(min(self.output_data)-0.001,max(self.output_data)+0.001) 
        return self.output_data

    def animate_relative_voltage_spectrum(self, averages=10):
        fig, ax = plt.subplots()
        ax.set_xlabel("Frequency (Hz)")
        ax.set_ylabel("Relative voltage noise density $\\sqrt{\\mathrm{Hz}}^{-1}$")
        ax.set_xscale("log")
        ax.set_yscale("log")
        noise = PowerSpectrum(DEFAULT_GET_DATA_LENGTH, self.sample_time)
        line, = ax.plot([], [])

        def worker(frame):
            print(frame)  # frame 0 is run twice. TODO: it should only run one time.
            data = self.get_error_data()
            if frame < averages:
                noise.add_data(data)
            else:
                noise.update_data(data)
            line.set_data(noise.f, noise.relative_voltage_spectrum)
            ax.set_ylim(min(noise.relative_voltage_spectrum), max(noise.relative_voltage_spectrum))
            ax.set_xlim(min(noise.f), max(noise.f))

        ani = animation.FuncAnimation(
            fig=fig,
            func=worker,
            init_func = lambda: None # TODO: this should be the only change needed to stop frame 0 from going twice
        )
        plt.show()

    def close(self):
        self.device.close()
