import serial
import numpy as np
import struct


DEFAULT_GET_DATA_LENGTH = 30000
BYTES_PER_FLOAT = 4 

class Quarto:
    def __init__(self, location='/dev/ttyACM6'):
        self.address = location
        self.device = serial.Serial(
            self.address,
            baudrate=115200,
            timeout=0.22
        )
        self.device.reset_input_buffer()
        self.device.reset_output_buffer()
        
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

