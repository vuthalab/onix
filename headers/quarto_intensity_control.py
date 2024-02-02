import serial
import time
import re
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import animation
from onix.analysis.debug.laser_linewidth import LaserLinewidth
from onix.analysis.power_spectrum import PowerSpectrum

samples_per_call = 50000 # how many samples the Quarto returns every time you ask for error or control data; will be changed soon

class Quarto:
    """
    Error in calculating power spectrums. 
    """
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
    
    def get_error_data(self):
        self.error_data = []
        self.device.reset_input_buffer()
        self.device.reset_output_buffer()
        out = "error_data\n"
        self.device.write(out.encode('utf-8'))
        for i in range(samples_per_call): 
            try:
                self.error_data.append(float(self.device.readline().decode('utf-8').strip('\n')))
            except ValueError as e:
                print(i)
                raise e
        self.error_data = np.asarray(self.error_data)

        return self.error_data
    
    def get_output_data(self):
        self.output_data = []
        self.device.reset_input_buffer()
        self.device.reset_output_buffer()
        out = "output_data\n"
        self.device.write(out.encode('utf-8'))
        for i in range(samples_per_call): 
            try:
                self.output_data.append(float(self.device.readline().decode('utf-8').strip('\n')))
            except ValueError as e:
                print(i)
                raise e
        self.output_data = np.asarray(self.output_data)

        return self.output_data

    def plot_error_data(self):
        a = self.get_error_data()
        ts = np.arange(0,len(a))
        ts = ts*self.sample_time

        plt.plot(ts, a)
        plt.xlabel("time [s]")
        plt.ylabel("error voltage [V]")
        plt.show()

    def plot_output_data(self):
        a = self.get_output_data()
        ts = np.arange(0,len(a))
        ts = ts*self.sample_time

        plt.plot(ts, a)
        plt.xlabel("time [s]")
        plt.ylabel("output voltage [V]")
        plt.show()

    def _calculate_fft(self, repeats = 10):
        self.repeats = repeats 
        voltages = []
        for i in range(self.repeats):
            voltages.append(self.get_error_data())
            time.sleep(0.2)
            
        noise = PowerSpectrum(voltages, self.sample_time)
        self.f = noise.f
        self.laser_noise = noise.power_spectrum
        self.fractional_noise = noise.relative_power_spectrum

    def plot_noise(self, repeats = 10):
        self._calculate_fft(repeats)
        plt.plot(self.f, self.laser_noise)
        plt.xscale("log")
        plt.yscale("log")
        plt.xlabel("Frequency (Hz)")
        plt.ylabel("Voltage noise density (V/$\\sqrt{\\mathrm{Hz}}$)")
        plt.tight_layout()
        plt.show()

    def plot_fractional_noise(self, repeats = 10):
        self._calculate_fft(repeats)
        plt.plot(self.f, self.fractional_noise)
        plt.xscale("log")
        plt.yscale("log")
        plt.xlabel("Frequency (Hz)")
        plt.ylabel("Fractional voltage noise density $\\sqrt{\\mathrm{Hz}}^{-1}$")
        plt.tight_layout()
        plt.show()
        
    def _animate_error(self, frame):
        self.get_error_data()
        t = np.linspace(0,len(self.error_data), len(self.error_data))
        t = t * self.sample_time
        self.line.set_data(t, self.error_data)
        self.axe.set_ylim(min(self.error_data-0.001),max(self.error_data)+0.001)
        return self.error_data

    def animated_error_data(self): # would be better to have these update, not refresh
        fig = plt.figure()

        self.get_error_data()
        t = np.linspace(0,len(self.error_data), len(self.error_data))
        t = t * self.sample_time

        self.axe = plt.axes()
        self.line, = self.axe.plot(t, self.error_data)
        plt.xlabel("time [s]")
        plt.ylabel("error voltage [V]")

        ani = animation.FuncAnimation(fig=fig, func=self._animate_error, frames = 10, interval=10, blit=False)
        plt.show()


    def _animate_output(self, frame):
        self.get_output_data()
        t = np.linspace(0,len(self.output_data), len(self.output_data))
        t = t*self.sample_time
        self.line.set_data(t, self.output_data)
        self.axe.set_ylim(min(self.output_data)-0.001,max(self.output_data)+0.001) 
        return self.output_data

    def animated_output_data(self): # would be better to have these update, not refresh
        fig = plt.figure()

        self.get_output_data()
        t = np.linspace(0,len(self.output_data), len(self.output_data))
        t = t*self.sample_time

        self.axe = plt.axes()
        self.axe.set_ylim(min(self.output_data)-0.01,max(self.output_data)+0.01)

        self.line, = self.axe.plot(t, self.output_data)
        plt.xlabel("time [s]")
        plt.ylabel("output voltage [V]")

        ani = animation.FuncAnimation(fig=fig, func=self._animate_output, frames = 10, interval=10, blit=False)

        plt.show()
        
    def _animated_fft_first_n(self, repeats = 10):
        self.fig = plt.figure()

        self.repeats = repeats 
        self.voltages = []
        self.voltages.append(self.get_error_data())
        time.sleep(0.2)

        self.noise = PowerSpectrum(self.voltages, self.sample_time)
        self.f = self.noise.f
        self.fractional_noise = self.noise.relative_power_spectrum

        self.axe = plt.axes()

        self.line, = self.axe.plot(self.f, self.fractional_noise)
        plt.xlabel("Frequency (Hz)")
        plt.ylabel("Fractional voltage noise density $\\sqrt{\\mathrm{Hz}}^{-1}$")
        plt.xscale("log")
        plt.yscale("log")

        ani = animation.FuncAnimation(fig=self.fig, func=self._animate_fft, frames = self.repeats - 1, repeat = False)
        plt.show()
    
    def _animate_fft_first_n(self, frame):
        new_trace = self.get_error_data()
        time.sleep(0.2)
        self.noise.add_data(new_trace)
        self.f = self.noise.f
        self.fractional_noise = self.noise.relative_power_spectrum
        self.line.set_data(self.f, self.fractional_noise)
        self.axe.set_ylim(min(self.fractional_noise),max(self.fractional_noise))
        self.axe.set_xscale("log")
        self.axe.set_yscale("log")

        return self.fractional_noise
        
    def animated_fft(self, repeats = 10):
        self._animated_fft_first_n(repeats)
        ani = animation.FuncAnimation(fig=self.fig, func=self._animate_fft, cache_frame_data = False)
        plt.show()
    
    def animated_fft_delay(self, repeats = 10):
        fig = plt.figure()

        self.repeats = repeats 
        self.voltages = []
        for i in range(self.repeats):
            self.voltages.append(self.get_error_data())
            time.sleep(0.2)

        self.noise = PowerSpectrum(self.voltages, self.sample_time)
        self.f = self.noise.f
        self.fractional_noise = self.noise.relative_power_spectrum

        self.axe = plt.axes()

        self.line, = self.axe.plot(self.f, self.fractional_noise)
        plt.xlabel("Frequency (Hz)")
        plt.ylabel("Fractional voltage noise density $\\sqrt{\\mathrm{Hz}}^{-1}$")
        plt.xscale("log")
        plt.yscale("log")

        ani = animation.FuncAnimation(fig=fig, func=self._animate_fft, cache_frame_data = False)
        plt.show()
    
    def _animate_fft(self, frame):
        new_trace = self.get_error_data()
        time.sleep(0.2)
        self.noise.update_data(new_trace)
        self.f = self.noise.f
        self.fractional_noise = self.noise.relative_power_spectrum
        self.line.set_data(self.f, self.fractional_noise)
        self.axe.set_ylim(min(self.fractional_noise),max(self.fractional_noise))
        self.axe.set_xscale("log")
        self.axe.set_yscale("log")

        return self.fractional_noise
    
    def close(self):
        self.device.close()
