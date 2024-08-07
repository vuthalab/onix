import numpy as np
import vxi11
from typing import Literal
import time

class Rigol():
    def __init__(self, address="192.168.0.123"):
        inst = vxi11.Instrument(f"TCPIP0::{address}::INSTR")
        name = "Rigol Technologies,DG4"
        if inst.ask("*IDN?")[0:len(name)] != name:
            raise ValueError("Address does not link to a Rigol series DG4000.")
        self._address = address
        self._inst = inst



    def ask(self, str):
        return self._inst.ask(str)
    
    def write(self, str):
        self._inst.write(str)
    


    def is_ch_on(self, ch: Literal[1, 2]):
        """
        Return boolean if ch [1, 2] is on.
        """
        return True if self.ask(f"OUTPUT{ch}?") == "ON" else False
        
    def set_ch_on_off(self, ch: Literal[1, 2], state: bool):
        """
        Set ch [1, 2] on with boolean.
        """
        self.write(f"OUTPUT{ch} {"ON" if state else "OFF"}")



    def field_plate_output(self, 
                     amplitude: float = 1, 
                     ramp_time: float = 1e-3, 
                     on_time: float = 10e-3,
                     number_steps: int = 256,
                     sign: Literal[-1, 1] = 1,
                     set_params: bool = False):
        
        """
        Use set_params = True if changing period, voltage, or other params excluded from arguments.
        """
        period = (on_time+ramp_time) * 1.1
        times = np.linspace(0, period, number_steps)
        ys = sign * amplitude/5 * (1/ramp_time*times*(times < ramp_time) + (times >= ramp_time)*(times < (on_time+ramp_time)))
        self.write(":OUTPUT1:STATE OFF")
        self.write("SOURCE1:TRACE:DATA VOLATILE,"+ ",".join(map(str, ys)))
        if set_params:
            v_high = 10
            v_low = -10
            self.write("SOURCE1:VOLTAGE:UNIT V")
            self.write("SOURCE1:VOLTAGE:LOW {:f}".format(v_low))
            self.write("SOURCE1:VOLTAGE:HIGH {:f}".format(v_high))
            self.write("SOURCE1:PERIOD {:f}".format(period))
            self.write("SOURCE1:BURSt:MODE TRIGgered")

        self.write("SOURCE1:BURSt ON")
        self.write(":OUTPUT1:STATE ON")
        
        
# rigol = Rigol()
# print(rigol.is_ch_on(1))
# print(rigol.is_ch_on(2))
# rigol.set_ch_on_off(1, True)
# start_time = time.time()
# rigol.field_plate_output()
# print(time.time()-start_time)

# inst = vxi11.Instrument('TCPIP0::192.168.0.123::INSTR')
# print(inst.ask('*IDN?'))

# period = 2e-6 # 2us
 
# v_high_1 = 0.5
# v_low_1 = -1*v_high_1
 
# v_high_2 = 2.5
# v_low_2 = -1*v_high_2

# samples = 2**12 # 4096 samples
# time=np.linspace(0,period,samples)
 
 
# y2=np.sin(time/period*2**5*2*np.pi)**2
# y1=-1+2*(time >= 10e-9)
  
  
# val_str_1 = ",".join(map(str,y1))
# val_str_2 = ",".join(map(str,y2))
  
  
# ### you can also automate some other stuff
# ### see the programmers manual of the RIGOL DG4000 series
# print(inst.ask("OUTPUT1?"))
# print(inst.ask("OUTPUT2?"))

# inst.write("OUTPUT1 ON")
# inst.write("SOURCE1:TRACE:DATA VOLATILE,"+ val_str_1)
# inst.write("SOURCE1:VOLTAGE:UNIT VPP")
# print(inst.ask("SOURCE1:VOLTAGE:UNIT?"))
# inst.write("SOURCE1:VOLTAGE:LOW {:f}".format(v_low_1))
# inst.write("SOURCE1:VOLTAGE:HIGH {:f}".format(v_high_1))
# inst.write("SOURCE1:PERIOD {:f}".format(period))
# inst.write("SOURCE1:BURSt ON")
# print(inst.ask("SOURCE1:BURST?"))
# inst.write("SOURCE1:BURSt:MODE TRIGgered")
# print(inst.ask("SOURCE1:BURST:MODE?"))
 