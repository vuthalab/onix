import serial
import time
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import animation
from onix.analysis.power_spectrum import PowerSpectrum


DEFAULT_GET_DATA_LENGTH = 1000

class Quarto:
    def __init__(self, location='/dev/ttyACM1'):
        self.address = location
        self.device = serial.Serial(self.address,
                                    baudrate=115200,
                                    timeout=0.2)
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

    def get_state(self):
        val = int(self._get_param("state"))
        self.state = val
        return val

    def get_integral(self):
        val = float(self._get_param("integral"))
        self.integral = val
        return val

    def get_scan(self):
        val = float(self._get_param("output_scan"))
        self.scan = val
        return val

    def get_last_transmission_point(self):
        val = float(self._get_param("last_transmission_point"))
        return val

    def get_last_output_point(self):
        val = float(self._get_param("last_output_point"))
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

    def set_scan(self, val):
        val = float(self._set_param("output_scan", val))
        self.scan = val
        return val

    def set_state(self, val):
        val = int(self._set_param("state", val))
        self.state = val
        return val

    def output_limit_indicator(self):
        """
        Prints warnings if integrator and output are near (within 10% of) their limits or outside of their limits.
        """
        val = int(self._get_param("limit_warnings"))

        if (val // 2**0) % 2 == 1:
            integral_warning = "Integral warning"
        elif (val // 2**1) % 2 == 1:
            integral_warning = "Integral out of bounds"
        else:
            integral_warning = "Integrator good"

        if (val // 2**2) % 2 == 1:
            output_warning = "Output warning"
        elif (val // 2**3) % 2 == 1:
            output_warning = "Output out of bounds"
        else:
            output_warning = "Output good"

        return integral_warning, output_warning

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
    
    def get_cavity_error_data(self, val = None):
        """
        Returns list of output data
        """
        if val is None:
            val = DEFAULT_GET_DATA_LENGTH
        self.cavity_error_data = []
        self.device.reset_input_buffer()
        self.device.reset_output_buffer()
        out = "cavity_error_data"  + str(val) + "\n"
        self.device.write(out.encode('utf-8'))
        for i in range(val):
            try:
                self.cavity_error_data.append(float(self.device.readline().decode('utf-8').strip('\n')))
            except ValueError as e:
                print(i)
                raise e
        self.cavity_error_data = np.asarray(self.cavity_error_data)

        return self.cavity_error_data

    def get_all_data(self):
        length = 1000
        self.device.reset_input_buffer()
        self.device.reset_output_buffer()
        out = "all_data\n"
        self.device.write(out.encode('utf-8'))
        error_data = []
        for i in range(length):
            try:
                error_data.append(float(self.device.readline().decode('utf-8').strip('\n')))
            except ValueError as e:
                print(i)
                raise e
        output_data = []
        for i in range(length):
            try:
                output_data.append(float(self.device.readline().decode('utf-8').strip('\n')))
            except ValueError as e:
                print(i)
                raise e
        transmission_data = []
        for i in range(length):
            try:
                transmission_data.append(float(self.device.readline().decode('utf-8').strip('\n')))
            except ValueError as e:
                print(i)
                raise e
        cavity_error_data = []
        for i in range(length):
            try:
                cavity_error_data.append(float(self.device.readline().decode('utf-8').strip('\n')))
            except ValueError as e:
                print(i)
                raise e
        return {
            "error": error_data,
            "output": output_data,
            "transmission": transmission_data,
            "cavity_error": cavity_error_data,
        }
    
    def get_dc_offset(self):
        val = float(self._get_param("dc_offset"))
        self.dc_offset = val
        return val    
    
    def set_dc_offset(self, val):
        val = float(self._set_param("dc_offset", val))
        self.dc_offset = val
        return val
    
    def get_unlock_counter(self):
        val = float(self._get_param("unlock_counter"))
        self.unlock_counter = val
        return val    
    
    def set_unlock_counter(self, val):
        val = float(self._set_param("unlock_counter", val))
        self.unlock_counter = val
        return val

    def close(self):
        self.device.close()

