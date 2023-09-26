import numpy as np
import datetime
import time
import os

from pymodbus.client import ModbusTcpClient
from struct import unpack


class PulseTube:
    def __init__(self,address='192.168.0.101'):
        self.device = ModbusTcpClient(address)
        if self.device.connect(): print(f"connected to pulse tube @ {address} \n")

        self.status_dict = {
            (0,0): "idling ‐ ready to start",
            (0,2): "starting",
            (0,3): "running",
            (0,5): "stopping",
            (0,6): "error lockout",
            (0,7): "error",
            (0,8): "helium cool down",
            (0,9): "power related error",
            (0,15): "recovered from error",
            (0,16): "must resolve previous error before starting again",
            (1,0): "compressor not energized",
            (1,1): "compressor energized",
        }

        #               'variable': (starting_register_number, value)
        self.variables = {
            'coolant in temp [C]': (6,0),
            'coolant out temp [C]': (8,0),
            'oil temp [C]': (10,0),
            'helium temp [C]': (12,0),
            'low pressure [psi]': (16,0),
            'high pressure [psi]': (20,0),
            'motor current [A]': (24,0),
            'hours': (26,0)
        }

        print('Initial Status:')
        self.status()


    def _modbus_to_float(self,num1,num2):
        a = num1.to_bytes(2,'big')
        b = num2.to_bytes(2,'big')
        X = np.asarray( [a[1].to_bytes(1,'big'),
                        a[0].to_bytes(1,'big'),
                        b[1].to_bytes(1,'big'),
                        b[0].to_bytes(1,'big')])
        # print(X)
        return unpack('f',X)[0]

    def is_on(self):
        power_state = self.device.read_input_registers(0x01,count=1).registers[0]
        return power_state == 3


    def status(self, silent=False):
        status = self.device.read_input_registers(0x01,count=40)
        regs = status.registers
        self._parse_status(regs, silent)

    def off(self):
        self.device.write_register(0x01,0x00FF)

    def on(self):
        self.device.write_register(0x01,0x0001)

    def close(self):
        self.device.close()

    def _parse_status(self, regs, silent=False):
        # qualitative diagnostics
        if not silent:
            for i in range(2):
                print(self.status_dict[(i,regs[i])])

        # quantitative diagnostics
        for k in self.variables.keys():
            regnum,value = self.variables[k]
            # convert each returned value into a sensible float
            # using the stupid modbus encoding: 2 ints, each of 2 bytes --> 1 float, 4 bytes
            value = self._modbus_to_float(regs[regnum],regs[regnum+1])

            # update value in variables dictionary
            self.variables[k] = (regnum,value)

            if not silent:
                print(f"{k} = {self.variables[k][1]:.3f}")

    def keep_logging(self,logging_interval=2000,sleep_time=100):
        print("[ Logging mode entered. Use Ctrl + I to interrupt. ]")
        try:
            while True:
                print(".",end='')
                timestamp = time.time()
                if timestamp % logging_interval <= 100:
                    print()
                    loc_time = time.ctime(timestamp)
                    print(f"@ {loc_time}")
                    self.status()
                    with open("/home/onix/Desktop/pulsetube_log.txt",'a') as f:
                        f.write(f"{timestamp}\t{self.variables}\n")
                        # to read back: use y = readline.split('\t') and eval() on y [1]
                time.sleep(sleep_time)
        except KeyboardInterrupt:
            print("[ exiting logging mode ]")

# ---------------------------------

if __name__ == '__main__':
    pt = PulseTube()
# pt.keep_logging(2000)


# for modbus:
# 0xxxx is read/write digital outputs ("coils")
# 1xxxx is read digital inputs
# 3xxxx is read input registers
# 4xxxx is read/write output channels or holding registers
#
# the prefixes are optional, as the function (eg, read_input_registers()) already picks out 3xxxx registers

# from the manual:
# The registers used for this protocol are as follows:
#
# 30,001 ‐ Operating State
# 30,002 ‐ Compressor Running
# 30,003 ‐ Warning State
# 30,005 ‐ Alarm State
# 30,007 ‐ Coolant In Temp
# 30,009 ‐ Coolant Out Temp
# 30,011 ‐ Oil Temp
# 30,013 ‐ Helium Temp
# 30,015 ‐ Low Pressure
# 30,017 ‐ Low Pressure Average
# 30,019 ‐ High Pressure
# 30,021 ‐ High Pressure Average
# 30,023 ‐ Delta Pressure Average
# 30,025 ‐ Motor Current
# 30,027 ‐ Hours Of Operation
# 30,029 ‐ Pressure Scale
# 30,030 ‐ Temp Scale
# 30,031 ‐ Panel Serial Number
# 30,032 ‐ Model Major + Minor numbers
# 30,033 ‐ Software Rev
# 40,001 ‐ Enable / Disable the compressor
