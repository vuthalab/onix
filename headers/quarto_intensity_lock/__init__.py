import serial
import time
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
        self.backgrounds = {}
        
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

    def get_output_upper_limit(self):
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
        Prints warnings if integrator and output are near (within 10% of) their limits or outside of their limits.
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

        plt.plot(ts, data)
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

        plt.plot(ts, data)
        plt.xlabel("time [s]")
        plt.ylabel("output voltage [V]")
        plt.show()

    # TODO: check if there is a cleaner way that doesn't require this function
    def _calculate_spectrum(self, averages = 10):
        """
        averages: int
        Calculates the averaged voltage and power spectrums, both the absolute and relative.
        """
        noise = PowerSpectrum(DEFAULT_GET_DATA_LENGTH, self.sample_time)
        for i in range(averages):
            noise.add_data(self.get_error_data())
            time.sleep(0.2)

        self.f = noise.f
        self.voltage_spectrum = noise.voltage_spectrum
        self.relative_voltage_spectrum = noise.relative_voltage_spectrum
        self.power_spectrum = noise.power_spectrum
        self.relative_power_spectrum = noise.relative_power_spectrum

    def _spectrum_plot_details(self, ax, spectrum_type, background_subtraction = False):
        """
        Puts axes in log scales, labels axes appropriately depending on spectrum type.

        spectrum_type: string, the type of sepectrum to plot
            - "voltage spectrum"
            - "relative voltage spectrum"
            - "power spectrum"
            - "relative power spectrum"
        
        background_subtraction: bool, if true it adds "Background subtracted" to the y axis label
        """
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_xlabel("Frequency (Hz)")
        if spectrum_type == "voltage spectrum":
            ylabel = "Voltage noise density (V/$\\sqrt{\\mathrm{Hz}}$)"
        elif spectrum_type == "relative voltage spectrum":
            ylabel = "Relative voltage noise density $\\sqrt{\\mathrm{Hz}}^{-1}$"
        elif spectrum_type == "power spectrum":
            ylabel = "Power noise density ($V^2/ \\mathrm{Hz}$)"
        elif spectrum_type == "relative power spectrum":
            ylabel = "Relative power noise density $\\mathrm{Hz}^{-1}$"
        else:
            raise ValueError("spectrum_type is not one of the supported four types")
        
        if background_subtraction == True:
            ylabel = "Background subtracted " + ylabel
        
        ax.set_ylabel(ylabel)

    def plot_voltage_noise(self, averages = 10):
        """
        Plot voltage noise spectrum using averages.
        """
        self._calculate_spectrum(averages)
        fig, ax = plt.subplots()
        ax.plot(self.f, self.voltage_spectrum)
        self._spectrum_plot_details(ax, "voltage spectrum")
        plt.show()

    def plot_relative_voltage_noise(self, averages = 10):
        """
        Plot relative voltage noise spectrum using averages.
        """
        self._calculate_spectrum(averages)
        fig, ax = plt.subplots()
        ax.plot(self.f, self.relative_voltage_spectrum)
        self._spectrum_plot_details(ax, "relative voltage spectrum")
        plt.show()

    def plot_power_noise(self, averages = 10):
        """
        Plot power noise spectrum using averages
        """
        self._calculate_spectrum(averages)
        fig, ax = plt.subplots()
        ax.plot(self.f, self.power_spectrum)
        self._spectrum_plot_details(ax, "power spectrum")
        plt.show()

    def plot_relative_power_noise(self, averages = 10):
        """
        Plot relative power noise spectrum using averages.
        """
        self._calculate_spectrum(averages)
        fig, ax = plt.subplots()
        ax.plot(self.f, self.relative_power_spectrum)
        self._spectrum_plot_details(ax, "relative power spectrum")
        plt.show()

    def animated_error_data(self): # would be better to have these update, not refresh
        """
        Creates refreshing plot of error data
        """
        fig, ax = plt.subplots()
        line, = ax.plot([], [])
        ax.set_xlabel("Time [s]")
        ax.set_ylabel("Error Voltage [V]")
        t = np.linspace(0, DEFAULT_GET_DATA_LENGTH, DEFAULT_GET_DATA_LENGTH)

        def worker(frame):
            """
            Updates frames when animating error data
            """
            data = self.get_error_data()
            self.line.set_data(t, data)
            self.axe.set_ylim(min(data)-0.001,max(data)+0.001) 

        ani = animation.FuncAnimation(
            fig=fig,
            func=worker,
            init_func = lambda: None,
            interval = 10,
            cache_frame_data = False,
            blit=False
        )
        plt.show()

    def animated_output_data(self): # would be better to have these update, not refresh
        """
        Creates refreshing plot of output data
        """
        fig, ax = plt.subplots()
        line, = ax.plot([], [])
        ax.set_xlabel("Time [s]")
        ax.set_ylabel("Output Voltage [V]")
        t = np.linspace(0, DEFAULT_GET_DATA_LENGTH, DEFAULT_GET_DATA_LENGTH)

        def worker(frame):
            """
            Updates frames when animating output data
            """
            data = self.get_output_data()
            self.line.set_data(t, data)
            self.axe.set_ylim(min(data)-0.001,max(data)+0.001) 

        ani = animation.FuncAnimation(
            fig=fig,
            func=worker,
            init_func = lambda: None,
            interval = 10,
            cache_frame_data = False,
            blit=False
        )
        plt.show()

    def _aniamted_spectrum(self, spectrum_type, averages, background_subtraction = False, background = None):
        fig, ax = plt.subplots()
        self._spectrum_plot_details(ax, spectrum_type, background_subtraction)
        noise = PowerSpectrum(DEFAULT_GET_DATA_LENGTH, self.sample_time)
        line, = ax.plot([], [])

        def worker(frame):
            data = self.get_error_data()
            if frame < averages:
                noise.add_data(data)
            else:
                noise.update_data(data)

            # TODO: will this be too inefficient for animating a spectrum? Probably, as in every frame you go through the same unnecesary if statements
            if background_subtraction == False:
                if spectrum_type == "voltage spectrum":
                    line.set_data(noise.f, noise.voltage_spectrum)
                    ax.set_ylim(min(noise.voltage_spectrum), max(noise.voltage_spectrum))
                elif spectrum_type == "relative voltage spectrum":
                    line.set_data(noise.f, noise.relative_voltage_spectrum)
                    ax.set_ylim(min(noise.relative_voltage_spectrum), max(noise.relative_voltage_spectrum))
                elif spectrum_type == "power spectrum":
                    line.set_data(noise.f, noise.power_spectrum)
                    ax.set_ylim(min(noise.power_spectrum), max(noise.power_spectrum))
                elif spectrum_type == "relative power spectrum":
                    line.set_data(noise.f, noise.relative_power_spectrum)
                    ax.set_ylim(min(noise.relative_power_spectrum), max(noise.relative_power_spectrum))
            elif background_subtraction == True:
                    background_subtracted_spectrum = [noise.power_spectrum[i] - self.backgrounds[background][i] for i in len(self.power_spectrum)]
                    line.set_data(noise.f, background_subtracted_spectrum)
                    ax.set_ylim(min(background_subtracted_spectrum), max(background_subtracted_spectrum))

            ax.set_xlim(min(noise.f), max(noise.f))

        ani = animation.FuncAnimation(
            fig=fig,
            func=worker,
            init_func = lambda: None,
            interval = 10, # TODO: interval is time between frames in ms. Find the appropriate value
            cache_frame_data = False,
            blit=False # TODO: blitting should make the animation faster. Verify this is true
        )
        plt.show()

    def animate_voltage_spectrum(self, averages=10):
        self._aniamted_spectrum("voltage spectrum", averages)
        
    def animate_relative_voltage_spectrum(self, averages=10):
        self._aniamted_spectrum("relative voltage spectrum", averages)

    def animate_power_spectrum(self, averages=10):
        self._aniamted_spectrum("power spectrum", averages)
        
    def animate_relative_power_spectrum(self, averages=10):
        self._aniamted_spectrum("relative power spectrum", averages)

    def new_background(self, name, averages = 10):
        """
        name: string
        averages: int
        Saves a new background power spectrum in the dictionary self.backgrounds under the specifed name
        """
        noise = PowerSpectrum(DEFAULT_GET_DATA_LENGTH, self.sample_time)
        for i in range(averages):
            noise.add_data(self.get_error_data())

        self.backgrounds[name] = noise.power_spectrum
    
    def remove_background(self, name):
        """
        name: string
        Remove a background that you no longer need
        """
        del self.backgrounds[name]

    def plot_background_subtracted_spectrum(self, background, averages = 10):
        """
        background: str, which background spectrum you want to subtract
        averages: int,
        Take a power spectrum with averages, and remove the specified background
        """
        self._calculate_spectrum(averages)
        fig, ax = plt.subplots()
        background_subtracted_spectrum = [self.power_spectrum[i] - self.backgrounds[background][i] for i in len(self.power_spectrum)]
        ax.plot(self.f, background_subtracted_spectrum)
        self._spectrum_plot_details(ax, "power spectrum", background_subtraction = True)
        plt.show()

    def animate_background_subtracted_spectrum(self, background, averages = 10):
        self._aniamted_spectrum("power spectrum", averages, background_subtraction = True, background = background)

    def close(self):
        self.device.close()

