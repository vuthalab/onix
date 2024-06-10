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

    @property
    def adc_interval(self): # TODO: does not return the actual adc rate
        self.device.reset_input_buffer()
        self.device.reset_output_buffer()
        out = "adc_interval\n"
        self.device.write(out.encode('utf-8'))
        response = self.device.readline().decode('utf-8')
       
        actual_response = ''.join([i for i in response if i.isdigit() or i == '.'])
        return float(actual_response)*1e-6  # [s]
        
    def data(self, val = None):
        if val is None:
            val = DEFAULT_GET_DATA_LENGTH
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

