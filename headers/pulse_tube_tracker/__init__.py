import serial
import numpy as np


class Quarto:
    def __init__(self, location='/dev/ttyACM3'):
        self.address = location
        self.device = serial.Serial(
            self.address,
            baudrate=115200,
            timeout=0.22
        )
        self.device.reset_input_buffer()
        self.device.reset_output_buffer()

    # def _query(self, name):
    #     out = name + '\n'
    #     self.device.write(out.encode('utf-8'))
    #     response = self.device.readline()
    #     response = response.decode('utf-8').strip('\n')
    #     return response

    # def setup(self, segment_length: int, segment_number: int):
    #     self.total_points = segment_length * segment_number
    #     response = self._query(f"setup {segment_length} {segment_number}")
    #     return response

    # def start(self):
    #     response = self._query("start")
    #     return response

    # def stop(self):
    #     response = self._query("stop")
    #     return response

    # def trigger(self):
    #     response = self._query("trigger")
    #     return response

    # def data(self):
    #     self.device.write("data\n".encode('utf-8'))
    #     ch1_data = []
    #     for kk in range(self.total_points):
    #         ch1_data.append(float(self.device.readline().decode('utf-8').strip('\n')))
    #     return np.array(ch1_data)
        
    def data(self, num_points):
        out = "data " + str(num_points) + '\n'
        self.device.write(out.encode('utf-8'))
        ch1_data = []
        for kk in range(num_points):
            ch1_data.append(float(self.device.readline().decode('utf-8').strip('\n')))
        return np.array(ch1_data)

    def close(self):
        self.device.close()

