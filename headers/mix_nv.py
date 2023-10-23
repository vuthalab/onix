from xmlrpc.client import boolean
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


# testing
# ser = serial.Serial('COM3', 
#                     9600,
#                     bytesize=serial.EIGHTBITS,
#                     timeout=10)

# ser.write(b'f0.0')
# ser.write(b'a7')
# ser.write(b'l1')

# ser.write(b'?')
# for i in range(18):
#     print(ser.readline().decode())
# # s = ser.read(500)
# ser.close()
# # print(s)
# print(ser.is_open)

# print('a{value:d}'.format(value=1))





class MixNV:
    def __init__(self):
        self.ser = serial.Serial('COM3', timeout=1)

    @property
    def frequency(self):
        self.ser.write(b'f?')
        return self.ser.readline().decode()

    @frequency.setter
    def frequency(self, value: float):
        self.ser.write(str.encode('f{value:.1f}'.format(value=value)))

    @property
    def power(self):
        self.ser.write(b'a?')
        return self.ser.readline().decode()

    @power.setter
    def power(self, value: int):
        if 0 < value <= 7:
            self.ser.write(str.encode('f{value:d}'.format(value=value)))

    @property
    def phase_lock(self):
        self.ser.write(b'p?')
        return self.ser.readline().decode()

    @phase_lock.setter
    def phase_lock(self, value: boolean):
            value = int(value)
            self.ser.write(str.encode('f{value:d}'.format(value=value)))

    @property
    def LO_mode(self):
        self.ser.write(b'l?')
        return self.ser.readline().decode()

    @LO_mode.setter
    def LO_mode(self, value: boolean):
            value = int(value)
            self.ser.write(str.encode('f{value:d}'.format(value=value)))

    @property
    def reference(self):
        self.ser.write(b'x?')
        return self.ser.readline().decode()

    @reference.setter
    def reference(self, value: boolean):
            value = int(value) # 1 internal - 0 external
            self.ser.write(str.encode('f{value:d}'.format(value=value)))

    @property
    def reference_frequency(self):
        self.ser.write(b'Y?')
        return self.ser.readline().decode()

    @reference_frequency.setter
    def reference_frequency(self, value: int):
        self.ser.write(str.encode('f{value:d}'.format(value=value)))

if __name__ == '__main__':
    t = MixNV()
    t.power = 7
    t.frequency = 1000.0
    t.LO_mode = False
    # print(t.frequency)

# from windfreak import SynthHD

# class RFSynthesizer:
#     def __init__(self):
#         self.synth = SynthHD('/dev/ttyACM0')
#         self.synth.init()

#         self.active_channel = 1

#     @property
#     def _channel(self):
#         return self.synth[self.active_channel-1]

#     @property
#     def power(self):
#         return self._channel.power

#     @power.setter
#     def power(self, value: float):
#         assert value <= 10
#         self._channel.power = value

#     @property
#     def frequency(self):
#         return self._channel.frequency

#     @frequency.setter
#     def frequency(self, value: float):
#         self._channel.frequency = value

#     @property
#     def enabled(self):
#         return self._channel.enable

#     @enabled.setter
#     def enabled(self, value: bool):
#         self._channel.enable = value

#     def on(self): self.enabled = True
#     def off (self): self.enabled = False

# if __name__ == '__main__':
#     synth = RFSynthesizer()
