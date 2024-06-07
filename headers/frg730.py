import serial
import numpy as np
import time

from uncertainties import ufloat

class FRG730:
    def __init__(self, address = '/dev/ttyUSB0'):
        self._gauge = serial.Serial(address,baudrate=9600,stopbits=1,parity='N',timeout=0.1)
        self._last_reading = (None, None)
        self.set_torr()
        self.units = 'torr'
        # units is one of these three strings: "torr", "mbar". "Pa"

    def read(self, Nbyte):
        return self._gauge.read(Nbyte) #Reads Nbyte bytes from values being streamed by ion gauge

    def write(self, command):
        self._gauge.write(command)

    def close(self):
        self._gauge.close()

    @property
    def pressure(self):
        try:
            data = self.read(2048)
        except:
            # Return last reading for minor blips
            if time.time() - self._last_reading[1] < 10: return self._last_reading[0]
            return None

        # Decode data
        synchronization_byte = 7 # byte that denotes start of output string
        data_length = 9 # 9 bytes that are sent from the device every 6 ms
        buff = []

        pressures = []
        record_byte = False
        for byte in data:
            if byte == synchronization_byte:
                record_byte = True

            if record_byte: #Load list with one full output string
                buff.append(byte)

            if len(buff) == data_length:
                try:
                    pressure = 10**((buff[4]*256+buff[5])/4000 - 12.625) # Conversion from manual

                    # Avoid occasional bugs
                    if pressure > 5e-12: pressures.append(pressure)
                finally:
                    buff = []
                    record_byte = False

        if pressures:
            pressure = ufloat(np.mean(pressures), np.std(pressures))
        else:
            pressure = None
        self._last_reading = (pressure, time.time())
        return pressure

    def set_torr(self):
        #Sets units on gauge to torr
        command = bytes([3]) + bytes([16]) + bytes([142]) + bytes([1]) + bytes([159]) #From manual
        self._gauge.write(command)
        self.units = 'torr'

    def set_mbar(self):
        #Sets units on gauge to mbar
        command = bytes([3]) + bytes([16]) + bytes([142]) + bytes([0]) + bytes([158]) #From manual
        self._gauge.write(command)
        self.units = 'mbar'

    def set_Pa(self):
        #Sets units on gauge to mbar
        command = bytes([3]) + bytes([16]) + bytes([142]) + bytes([1]) + bytes([159]) #From manual
        self._gauge.write(command)
        self.units = 'Pa'

    def degas_on(self):
        #Turns on degas minute for 3 minutes, should only be turned on for pressures below <3e-6 torr
        command = bytes([3]) + bytes([16]) + bytes([196]) + bytes([1]) + bytes([213]) #From manual
        self._gauge.write(command)

    def degas_off(self):
        #Spots degas before 3 minutes are up
        command = bytes([3]) + bytes([16]) + bytes([196]) + bytes([0]) + bytes([212]) #From manual
        self._gauge.write(command)
