import serial
from onix.headers.find_quarto import find_quarto

from onix.units import ureg, Q_


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
    
    def _set_param(self, param, value):
        out = param + " " + str(value) + '\n'
        self.device.write(out.encode('utf-8'))
        response = self.device.readline()

    def V_low(self, value = None):
        if value is not None:
            self._set_param("V_low", value)
        else:
            return float(self._get_param("V_low"))

    def V_high(self, value = None):
        if value is not None:
            self._set_param("V_high", value)
        else:
            return float(self._get_param("V_high"))

    def error_counter(self):
        return int(self._get_param("error_counter"))

    def rise_ramp_time(self, value = None):
        if value is not None:
            self._set_param("rise_ramp_time", int(round(value.to("us").magnitude)))
        else:
            return int(self._get_param("rise_ramp_time") * ureg.us)

    def fall_ramp_time(self, value = None):
        if value is not None:
            self._set_param("fall_ramp_time", int(round(value.to("us").magnitude)))
        else:
            return int(self._get_param("fall_ramp_time") * ureg.us)

    def remove_all_pulses(self):
        self._set_param("remove_all_pulses", "")

    def add_pulse(self, rise_time, fall_time):
        rise_time_us = str(int(round(rise_time.to("us").magnitude)))
        fall_time_us = str(int(round(fall_time.to("us").magnitude)))
        self._set_param("pulse_time_us", f"{rise_time_us} {fall_time_us}")
    
    def close(self):
        self.device.close()

