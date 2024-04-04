import serial
import numpy as np


class Quarto:
    def __init__(self, location='/dev/ttyACM4'):
        self.address = location
        self.device = serial.Serial(
            self.address,
            baudrate=115200,
            timeout=0.2
        )
        self.device.reset_input_buffer()
        self.device.reset_output_buffer()

    def _query(self, name):
        out = name + '\n'
        self.device.write(out.encode('utf-8'))
        response = self.device.readline()
        response = response.decode('utf-8').strip('\n')
        return response

    def setup(self, segment_length: int, segment_number: int):
        response = self._query(f"setup {segment_length} {segment_number}")
        print(response)

    def start(self):
        response = self._query("start")
        print(response)

    def stop(self):
        response = self._query("stop")
        print(response)

    def data(self):
        triggers_too_soon = int(self._query("trigger_too_soon").split(" ")[-1])
        if triggers_too_soon > 0:
            raise RuntimeError(f"Triggered too soon {triggers_too_soon} times before data taking finished.")
        self.device.write("data\n".encode('utf-8'))
        ch1_length = int(self.device.readline().decode('utf-8').strip('\n'))
        ch1_data = []
        for kk in range(ch1_length):
            ch1_data.append(float(self.device.readline().decode('utf-8').strip('\n')))
        ch2_length = int(self.device.readline().decode('utf-8').strip('\n'))
        ch2_data = []
        for kk in range(ch2_length):
           ch2_data.append(float(self.device.readline().decode('utf-8').strip('\n')))
        return np.array([ch1_data, ch2_data])
        # return np.array(ch1_data)

    def close(self):
        self.device.close()

