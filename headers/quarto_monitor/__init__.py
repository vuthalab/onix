import serial
import numpy as np
import struct
from onix.headers.find_quarto import find_quarto

BYTES_PER_FLOAT = 4 

class Quarto:
    def __init__(self, location=find_quarto("digitizer"), num_channels = 4):
        self.address = location
        self.device = serial.Serial(
            self.address,
            baudrate=115200,
            timeout=0.22
        )
        self.device.reset_input_buffer()
        self.device.reset_output_buffer()

    def _get_param(self, param):
        out = param + '\n'
        self.device.write(out.encode('utf-8'))
        response = self.device.readline()
        response = response.decode('utf-8').strip('\r\n').split(" ")[-1]
        return response
    
    def adc_interval(self):
        adc_interval = round(int(self._get_param("adc_interval")) * 1e-6, 6) # TODO: without the rounding it always returns self._get_param("adc_interval")
        return adc_interval
    
    def data_time(self):
        data_time = round(int(self._get_param("data_time")) * 1e-6, 6)
        return data_time
    
    def max_data_length(self):
        max_data_length = int(self._get_param("max_data_length"))
        return max_data_length

    def data(self):
        out = "data" + '\n'
        self.device.write(out.encode('utf-8'))
        response = self.device.readlines()
        data = []
        for i in range(len(response)):
            numerical_value = float(response[i].decode('utf-8').strip('\n').split(" ")[-1])
            data.append(numerical_value)

        ch1 = data[ 0 : int(len(data) / 4) ]
        ch2 = data[ int(len(data) / 4) : int(2 * len(data) / 4) ]
        ch3 = data[ int(2 * len(data) / 4) : int(3 * len(data) / 4) ]
        ch4 = data[ int(3 * len(data) / 4) : int(len(data)) ]
        return ch1, ch2, ch3, ch4


    def close(self):
        self.device.close()

