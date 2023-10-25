import serial
import time

# ? gives not in manual:
#   phase lock detect (p)
#   reference (x)
#   reference frequency (Y)


# f) Frequency MHz 1000.0
# a) Power Setting (0-7) 7
# d) FM deviation (0-32760) 0
# r) FM burst repetitions (0-65535) 200
# t) FM mod step delay (uS) (0-65535) 500
# m) FM modulation control bit 0
# c) FM continuous modulation 0
# i) FM source (1=internal 0=external) 1
# b) Send one FM burst
# l) LO Mode (1=LO 0=Mixer) 1
# x) Reference (1=internal 0=external) 1
# e) Program EEPROM
# v) Firmware Version
# +) Model Type
# -) Serial Number 0
# ?) help


class MixNV:
    def __init__(self, port="ttyACM2"):
        self.ser = serial.Serial(port, timeout=0.1)

    @property
    def frequency(self):
        """Output frequency in MHz."""
        self.ser.write(b'f?')
        return float(self.ser.readline().decode())

    @frequency.setter
    def frequency(self, value: float):
        self.ser.write(str.encode('f{value:.1f}'.format(value=value)))

    @property
    def power(self):
        self.ser.write(b'a?')
        return int(self.ser.readline().decode())

    @power.setter
    def power(self, value: int):
        if value < 0 or value > 7 or int(value) != value:
            raise ValueError("Power must be an integer between 0 and 7.""")
        self.ser.write(str.encode('a{value:d}'.format(value=int(value))))

    @property
    def phase_lock(self):
        self.ser.write(b'p?')
        return bool(self.ser.readline().decode())

    @phase_lock.setter
    def phase_lock(self, value: bool):
        value = int(value)
        self.ser.write(str.encode('f{value:d}'.format(value=value)))

    @property
    def LO_mode(self):
        self.ser.write(b'l?')
        return bool(self.ser.readline().decode())

    @LO_mode.setter
    def LO_mode(self, value: bool):
        value = int(value)
        self.ser.write(str.encode('f{value:d}'.format(value=value)))

    @property
    def reference(self):
        """True is internal, false is external."""
        self.ser.write(b'x?')
        return bool(self.ser.readline().decode())

    @reference.setter
    def reference(self, value: bool):
        value = int(value) # 1 internal - 0 external
        self.ser.write(str.encode('f{value:d}'.format(value=value)))

    @property
    def reference_frequency(self):
        self.ser.write(b'Y?')
        return float(self.ser.readline().decode())

    @reference_frequency.setter
    def reference_frequency(self, value: float):
        self.ser.write(str.encode('f{value:d}'.format(value=value)))

if __name__ == '__main__':
    t = MixNV()
    t.power = 7
    t.frequency = 1000.0
    t.LO_mode = False

