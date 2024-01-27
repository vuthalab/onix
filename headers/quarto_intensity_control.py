import serial
import time
import re
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import animation
from onix.analysis.debug.laser_linewidth import LaserLinewidth


class Quarto:
    def __init__(self, location='/dev/ttyACM1'):
        self.address = location
        self.device = serial.Serial(self.address,
                                    baudrate=115200,
                                    timeout=0.2)

        self.sample_time = 2e-6
        self.sample_rate = 1/self.sample_time
        
        self.device.reset_input_buffer()
        self.device.reset_output_buffer()
        out = "state\n"
        self.device.write(out.encode('utf-8'))
        time.sleep(0.1)
        response = self.device.readlines()

    def _get_param(self, param):
        self.device.reset_input_buffer()
        self.device.reset_output_buffer()
        out = param + '\n'
        self.device.write(out.encode('utf-8'))
        time.sleep(0.1)
        response = self.device.readlines()[0].decode('utf-8').strip('\n')
        response = float(re.findall(r'\d+\.\d+', response)[0])
        print(param, ": ", response)
        return response

    def _set_param(self, param, val):
        self.device.reset_input_buffer()
        self.device.reset_output_buffer()
        out = param + " " + str(val) + '\n'
        self.state = val
        self.device.write(out.encode('utf-8'))
        time.sleep(0.1) #test without this
        response = self.device.readlines()[0].decode('utf-8').strip('\n')
        response = float(re.findall(r'\d+\.\d+', response)[0])
        print(param, ": ", response)
        return response

    def get_p_gain(self):
        self.p_gain = self._get_param("p_gain")    

    def get_i_time(self): #error
        self.i_time = self._get_param("i_time")

    def get_d_time(self):
        self.d_time = self._get_param("d_time")
    
    def get_integral_limit(self):
        self.integral_limit = self._get_param("integral_limit")

    def get_error_offset(self):
        self.error_offset = self._get_param("error_offset")

    def get_output_offset(self):
        self.output_offset = self._get_param("output_offset")

    def get_output_lower_limit(self):
        self.output_lower_limit = self._get_param("output_lower_limit")

    def get_output_uppper_limit(self):
        self.output_upper_limit = self._get_param("output_upper_limit")

    def get_pid_state(self):
        self.device.reset_input_buffer()
        self.device.reset_output_buffer()
        out = "pid_state\n"
        self.device.write(out.encode('utf-8'))
        time.sleep(0.1)
        response = str(self.device.readlines()[0])[15:16] 
        print("PID State: ", response)

    def set_p_gain(self, val):
        self.p_gain = self._set_param("p_gain", val)    

    def set_i_time(self, val):
        self.i_time = self._set_param("i_gain", val)

    def set_d_time(self, val):
        self.d_time = self._set_param("d_time", val)
    
    def set_integral_limit(self, val):
        self.integral_limit = self._set_param("integral_limit", val)

    def set_error_offset(self, val):
        self.error_offset = self._set_param("error_offset", val)

    def set_output_offset(self, val):
        self.output_offset = self._set_param("output_offset", val)

    def set_output_lower_limit(self, val):
        self.output_lower_limit = self._set_param("output_lower_limit", val)

    def set_output_upper_limit(self, val):
        self.output_upper_limit =self._set_param("output_upper_limit", val)

    def set_pid_state(self, val):
        self.device.reset_input_buffer()
        self.device.reset_output_buffer()
        out = "pid_state " + str(val) + '\n'
        self.state = val
        self.device.write(out.encode('utf-8'))
        time.sleep(0.1) #test without this
        response = str(self.device.readlines()[0])[15:16]
        print("PID State: ", response)
    
    def get_error_data(self):
        self.error_data = []
        self.device.reset_input_buffer()
        self.device.reset_output_buffer()
        out = "error_data\n"
        self.device.write(out.encode('utf-8'))
        for i in range(50000): 
            try:
                self.error_data.append(float(self.device.readline().decode('utf-8').strip('\n')))
            except ValueError as e:
                print(i)
                #raise e
                print(self.device.readline())
        self.error_data = np.asarray(self.error_data)

        return self.error_data
    
    def get_output_data(self):
        self.output_data = []
        self.device.reset_input_buffer()
        self.device.reset_output_buffer()
        out = "output_data\n"
        self.device.write(out.encode('utf-8'))
        for i in range(50000): 
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

        max_point_per_decade = 100
        discriminator_slope = 1  # unused
        noise = LaserLinewidth(voltages, 1 / self.sample_rate, discriminator_slope, max_point_per_decade)
        self.f = noise.f
        self.laser_noise = np.sqrt(noise.W_V)
        self.fractional_noise = self.laser_noise / np.average(voltages)

    def plot_noise(self):
        self._calculate_fft()
        plt.plot(self.f, self.laser_noise)
        plt.xscale("log")
        plt.yscale("log")
        plt.xlabel("Frequency (Hz)")
        plt.ylabel("Voltage noise density (V/$\\sqrt{\\mathrm{Hz}}$)")
        plt.tight_layout()
        plt.show()

    def plot_fractional_noise(self):
        self._calculate_fft()
        plt.plot(self.f, self.fractional_noise)
        plt.xscale("log")
        plt.yscale("log")
        plt.xlabel("Frequency (Hz)")
        plt.ylabel("Fractional voltage noise density $\\sqrt{\\mathrm{Hz}}^{-1}$")
        plt.tight_layout()
        plt.show()

    def _animate_fft(self, frame):
        self.voltages[self.i] = self.get_error_data()
        time.sleep(0.2)
        max_point_per_decade = 100
        discriminator_slope = 1  # unused
        noise = LaserLinewidth(self.voltages, 1 / self.sample_rate, discriminator_slope, max_point_per_decade)
        self.f = noise.f
        self.laser_noise = np.sqrt(noise.W_V)
        self.fractional_noise = self.laser_noise / np.average(self.voltages)
        self.line.set_data(self.f, self.fractional_noise)
        self.axe.set_ylim(min(self.fractional_noise),max(self.fractional_noise))
        self.axe.set_xscale("log")
        self.axe.set_yscale("log")

        if self.i < self.repeats - 1:
            self.i += 1
        else:
            self.i = 0

        return self.fractional_noise

    def animated_fft(self, repeats = 10):
        fig = plt.figure()

        self.repeats = repeats 
        self.voltages = []
        for i in range(self.repeats):
            self.voltages.append(self.get_error_data())
            time.sleep(0.2)

        max_point_per_decade = 100
        discriminator_slope = 1  # unused
        noise = LaserLinewidth(self.voltages, 1 / self.sample_rate, discriminator_slope, max_point_per_decade)
        self.f = noise.f
        self.laser_noise = np.sqrt(noise.W_V)
        self.fractional_noise = self.laser_noise / np.average(self.voltages)

        self.axe = plt.axes()

        self.line, = self.axe.plot(self.f, self.fractional_noise)
        plt.xlabel("Frequency (Hz)")
        plt.ylabel("Fractional voltage noise density $\\sqrt{\\mathrm{Hz}}^{-1}$")
        plt.xscale("log")
        plt.yscale("log")

        self.i = 0
        ani = animation.FuncAnimation(fig=fig, func=self._animate_fft)
        plt.show()

    def _animate_error(self, frame):
        self.get_error_data()
        t = np.linspace(0,len(self.error_data), len(self.error_data))
        t = t / self.sample_rate
        self.line.set_data(t, self.error_data)
        self.axe.set_ylim(min(self.error_data-0.001),max(self.error_data)+0.001)
        return self.error_data

    def animated_error_data(self):
        fig = plt.figure()

        self.get_error_data()
        t = np.linspace(0,len(self.error_data), len(self.error_data))
        t = t / self.sample_rate

        self.axe = plt.axes()
        self.line, = self.axe.plot(t, self.error_data)
        plt.xlabel("time [s]")
        plt.ylabel("error voltage [V]")

        ani = animation.FuncAnimation(fig=fig, func=self._animate_error, frames = 10, interval=10, blit=False)
        plt.show()


    def _animate_output(self, frame):
        self.get_output_data()
        t = np.linspace(0,len(self.output_data), len(self.output_data))
        t = t*1e-6
        self.line.set_data(t, self.output_data)
        self.axe.set_ylim(min(self.output_data)-0.001,max(self.output_data)+0.001) #self.axe.set_ylim(min(self.errdata),max(self.errdata))
        return self.output_data

    def animated_output_data(self):
        fig = plt.figure()

        self.get_output_data()
        t = np.linspace(0,len(self.output_data), len(self.output_data))
        t = t*1e-6

        self.axe = plt.axes()
        self.axe.set_ylim(min(self.output_data)-0.01,max(self.output_data)+0.01)

        self.line, = self.axe.plot(t, self.output_data)
        plt.xlabel("time [s]")
        plt.ylabel("output voltage [V]")

        ani = animation.FuncAnimation(fig=fig, func=self._animate_output, frames = 10, interval=10, blit=False)

        plt.show()

    def close(self):
        self.device.close()
