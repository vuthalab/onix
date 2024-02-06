'''
Interface for Rigol DP832 Power Supply
Jan 2019, Harish Ramachandran & Mohit Verma. University of Toronto
'''

import numpy as np
import time
import os
import sys

class DM3068:
    def __init__(self,address='/dev/usbtmc0'):

        # allowed data formats are 'float32' or 'adc16'

        self.address = address
        self.FILE = os.open(address, os.O_RDWR) # this is the file object where commands are written & read


        if 'Rigol Technologies,DM3068,DM3O193700713,01.01.00.01.10.00'.encode() not in self.get_name(): print('Wrong device')
        else: print('Rigol Multimeter Loaded')

    def write(self, command):
        os.write(self.FILE, (command+"\n").encode())

    def read(self, length = 16000):
        return os.read(self.FILE, length)

    def ask(self, command):
        self.write(command)
        return self.read()

    def get_voltage(self):
        return float(self.ask(":MEAS:VOLT:DC?"))

    def get_name(self):
        return self.ask("*IDN?")
