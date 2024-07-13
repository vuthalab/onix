import serial
import numpy as np
import struct
from onix.headers.find_quarto import find_quarto

DEFAULT_GET_DATA_LENGTH = 30000 # max data you can transfer from the quarto at one time
BYTES_PER_FLOAT = 4 

class Quarto:
    def __init__(self, location=find_quarto("digitizer")):
        self.address = location
        self.device = serial.Serial(
            self.address,
            baudrate=115200,
            timeout=0.22
        )
        self.device.reset_input_buffer()
        self.device.reset_output_buffer()
        self.adc_interval = self.adc_interval_2()
        self.data_time = self.data_time()
        self.default_get_data_length = int(self.data_time / self.adc_interval)


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

    def adc_interval(self): # TODO: does not return the actual adc rate
        self.device.reset_input_buffer()
        self.device.reset_output_buffer()
        out = "adc_interval\n"
        self.device.write(out.encode('utf-8'))
        response = self.device.readline().decode('utf-8')
       
        actual_response = ''.join([i for i in response if i.isdigit() or i == '.']) # TODO: possibly fixed?
        return float(actual_response)*1e-6  # [s]
    
    def adc_interval_2(self):
        adc_interval = float(self._get_param("adc_interval")) * 1e-6
        return adc_interval
    
    def data_time(self):
        data_time = float(self._get_param("data_time"))
        return data_time

    def data(self, val = None):
        if val is None:
            val = self.default_get_data_length
        self.device.reset_input_buffer()
        self.device.reset_output_buffer()
        out = "data " + str(val) + "\n"
        self.device.write(out.encode('utf-8'))
        byte_data = self.device.read(val * BYTES_PER_FLOAT)
        num_points = str(val) + "f"
        data = struct.unpack(num_points, byte_data)
        self.array_data = np.asarray(data)
        return self.array_data

    def close(self):
        self.device.close()

