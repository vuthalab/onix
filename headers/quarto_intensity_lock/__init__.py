import serial
import time
import numpy as np
import struct
import matplotlib.pyplot as plt
from matplotlib import animation
from onix.analysis.power_spectrum import PowerSpectrum, CCedPowerSpectrum


DEFAULT_GET_DATA_LENGTH = 30000
BYTES_PER_FLOAT = 4 

class Quarto:
    def __init__(self, location='/dev/ttyACM1'):
        self.address = location
        self.device = serial.Serial(
            self.address,
            baudrate=115200,
            timeout=0.2
        )
        sample_time_us = float(self._get_param("adc_interval")) 
        self.sample_time = sample_time_us * 1e-6
        self.backgrounds = {}
        self.device.reset_input_buffer()
        self.device.reset_output_buffer()
        
    def _get_param(self, param):
        out = param + '\n'
        self.device.write(out.encode('utf-8'))
        response = self.device.readline()
        response = response.decode('utf-8').strip('\n').split(" ")[-1]
        return response

    def _set_param(self, param, val):
        out = param + " " + str(val) + '\n'
        self.state = val
        self.device.write(out.encode('utf-8'))
        response = self.device.readline()
        response = response.decode('utf-8').strip('\n').split(" ")[-1]
        return response
    
    def get_setpoint(self):
        val = float(self._get_param("pd_setpoint"))
        self.setpoint = val
        return val
    
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

    def get_pd_setpoint(self):
        val = float(self._get_param("pd_setpoint"))
        self.pd_setpoint = val
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
    
    def set_setpoint(self, val):
        val = float(self._set_param("pd_setpoint", val))
        self.setpoint = val
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

    def set_pd_setpoint(self, val):
        val = float(self._set_param("pd_setpoint", val))
        self.pd_setpoint = val
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
        
    def get_primary_pd_data(self, val = None):
        if val is None:
                val = DEFAULT_GET_DATA_LENGTH
        self.device.reset_input_buffer()
        self.device.reset_output_buffer()
        out = "primary_pd_data " + str(val) + "\n"
        self.device.write(out.encode('utf-8'))
        byte_data = self.device.read(DEFAULT_GET_DATA_LENGTH * BYTES_PER_FLOAT)
        num_points = str(DEFAULT_GET_DATA_LENGTH) + "f"
        data = struct.unpack(num_points, byte_data)
        self.primary_pd_data= np.asarray(data)
        return self.primary_pd_data
        
    def get_monitor_pd_data(self, val = None):
        if val is None:
            val = DEFAULT_GET_DATA_LENGTH
        self.device.reset_input_buffer()
        self.device.reset_output_buffer()
        out = "monitor_pd_data " + str(val) + "\n"
        self.device.write(out.encode('utf-8'))
        byte_data = self.device.read(DEFAULT_GET_DATA_LENGTH * BYTES_PER_FLOAT)
        num_points = str(DEFAULT_GET_DATA_LENGTH) + "f"
        data = struct.unpack(num_points, byte_data)
        self.monitor_pd_data = np.asarray(data)
        return self.monitor_pd_data
        
    def get_both_pd_data(self, val = None):
        if val is None:
            val = DEFAULT_GET_DATA_LENGTH
        all_data = []
        self.device.reset_input_buffer()
        self.device.reset_output_buffer()
        out = "both_pd_data " + str(val) + "\n"
        self.device.write(out.encode('utf-8'))
        byte_data = self.device.read(2 * DEFAULT_GET_DATA_LENGTH * BYTES_PER_FLOAT)
        num_points = str(2 * DEFAULT_GET_DATA_LENGTH) + "f"
        data = struct.unpack(num_points, byte_data)
        all_data = np.asarray(data)
        half = int(len(all_data) / 2)

        self.primary_pd_data = all_data[0:half]
        self.monitor_pd_data = all_data[half:]

        return (self.primary_pd_data, self.monitor_pd_data)
    
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

    def plot_error_data(self):  # TODO: update this.
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
    def _calculate_spectrum(self, averages = 10, max_points_per_decade: int = 200):
        """
        averages: int
        Calculates the averaged voltage and power spectrums, both the absolute and relative.
        """
        noise = PowerSpectrum(DEFAULT_GET_DATA_LENGTH, self.sample_time, max_points_per_decade)
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
            line.set_data(t, data)
            ax.set_xlim(0,DEFAULT_GET_DATA_LENGTH)
            ax.set_ylim(min(data)-0.001,max(data)+0.001) 

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
            line.set_data(t, data)
            ax.set_ylim(min(data)-0.001,max(data)+0.001) 

        ani = animation.FuncAnimation(
            fig=fig,
            func=worker,
            init_func = lambda: None,
            interval = 10,
            cache_frame_data = False,
            blit=False
        )
        plt.show()

    def _animated_spectrum(self, spectrum_type, averages, background_subtraction = False, background = None):
        fig, ax = plt.subplots()
        self._spectrum_plot_details(ax, spectrum_type, background_subtraction)
        noise = PowerSpectrum(DEFAULT_GET_DATA_LENGTH, self.sample_time, max_points_per_decade=200)
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
                    #ax.set_ylim(min(noise.voltage_spectrum), max(noise.voltage_spectrum))
                elif spectrum_type == "relative voltage spectrum":
                    line.set_data(noise.f, noise.relative_voltage_spectrum)
                    #ax.set_ylim(min(noise.relative_voltage_spectrum), max(noise.relative_voltage_spectrum))
                elif spectrum_type == "power spectrum":
                    line.set_data(noise.f, noise.power_spectrum)
                    #ax.set_ylim(min(noise.power_spectrum), max(noise.power_spectrum))
                elif spectrum_type == "relative power spectrum":
                    line.set_data(noise.f, noise.relative_power_spectrum)
                    #ax.set_ylim(min(noise.relative_power_spectrum), max(noise.relative_power_spectrum))
            elif background_subtraction == True:
                    background_subtracted_spectrum = [noise.power_spectrum[i] - self.backgrounds[background][i] for i in len(self.power_spectrum)]
                    line.set_data(noise.f, background_subtracted_spectrum)
                    #ax.set_ylim(min(background_subtracted_spectrum), max(background_subtracted_spectrum))

            ax.set_xlim(min(noise.f), max(noise.f))
            ax.set_ylim(5e-8, 8e-5)

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
        self._animated_spectrum("voltage spectrum", averages)
        
    def animate_relative_voltage_spectrum(self, averages=10):
        self._animated_spectrum("relative voltage spectrum", averages)

    def animate_power_spectrum(self, averages=10):
        self._animated_spectrum("power spectrum", averages)
        
    def animate_relative_power_spectrum(self, averages=10):  # TODO: reduce code duplication.
        self._animated_spectrum("relative power spectrum", averages)

    def animate_cross_correlated_spectrum(self, averages=10):
        fig, ax = plt.subplots()
        self._spectrum_plot_details(ax, "relative voltage spectrum", False)
        noise = CCedPowerSpectrum(DEFAULT_GET_DATA_LENGTH, self.sample_time, max_points_per_decade=200)
        line_primary, = ax.plot([], [], label="primary")
        line_monitor, = ax.plot([], [], label="monitor")
        line_cc, = ax.plot([], [], label="cross-correlation")
        line_bg_primary, = ax.plot(noise.f, [2e-7 for kk in noise.f], ls="--", label="noise bg primary", color="C0")
        line_bg_monitor, = ax.plot(noise.f, [2e-7 for kk in noise.f], ls="--", label="noise bg monitor", color="C1")
        legend = ax.legend()

        def worker(frame):
            primary_data, monitor_data = self.get_both_pd_data()
            if frame < averages:
                noise.add_data(primary_data, monitor_data)
            else:
                noise.update_data(primary_data, monitor_data)

            legend.get_texts()[0].set_text(f"primary: {noise.error_signal_1_average:.3f} V")
            legend.get_texts()[1].set_text(f"monitor: {noise.error_signal_2_average:.3f} V")

            line_bg_primary.set_data(noise.f, [2e-7 / noise.error_signal_1_average for kk in noise.f])
            line_bg_monitor.set_data(noise.f, [2e-7 / noise.error_signal_2_average for kk in noise.f])

            min_number = np.inf
            max_number = -np.inf
            v1_spectrum = noise.signal_1_relative_voltage_spectrum
            line_primary.set_data(noise.f, v1_spectrum)
            if min_number > np.min(v1_spectrum):
                min_number = np.min(v1_spectrum)
            if max_number < np.max(v1_spectrum):
                max_number = np.max(v1_spectrum)
            v2_spectrum = noise.signal_2_relative_voltage_spectrum
            line_monitor.set_data(noise.f, v2_spectrum)
            if min_number > np.min(v2_spectrum):
                min_number = np.min(v2_spectrum)
            if max_number < np.max(v2_spectrum):
                max_number = np.max(v2_spectrum)
            cc_spectrum = noise.cc_relative_voltage_spectrum
            line_cc.set_data(noise.f, cc_spectrum)
            if min_number > np.min(cc_spectrum):
                min_number = np.min(cc_spectrum)
            if max_number < np.max(cc_spectrum):
                max_number = np.max(cc_spectrum)
            ax.set_ylim(min_number, max_number)

        ani = animation.FuncAnimation(
            fig=fig,
            func=worker,
            init_func = lambda: None,
            interval = 100, # TODO: interval is time between frames in ms. Find the appropriate value
            cache_frame_data = False,
            blit=False # TODO: blitting should make the animation faster. Verify this is true
        )
        plt.show()


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
        self._animated_spectrum("power spectrum", averages, background_subtraction = True, background = background)

    def close(self):
        self.device.close()

