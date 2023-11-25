import numpy as np
import time
import matplotlib.pyplot as plt
import pyvisa
import serial

from onix.headers.DG4162 import DG4162
from onix.headers.awg.M4i6622 import M4i6622

m4i = M4i6622()
m4i.start_sine_outputs()
rm = pyvisa.ResourceManager('@py')
fg = DG4162(rm, rm.list_resources()[4]) #the DG4162 should be the at index 4 in the list of connected devices


###
def trigger():
    m4i.set_ttl_output(1, True)
    time.sleep(0.1)
    m4i.set_ttl_output(1, False)

fg.setPulse(
    channel = 1,
    highV = 1.5,
    lowV = -1,
    period = 1e-3,
    duty = 50,
    delay = 0
)

fg.setLeadTrailMinimum(channel = 1)

fg.ExtBurst(
    channel = 1,
    nCycl = 3,
    slope = 'positive')


#print(fg.getWaveformDetails(), '\n')
#print(fg.getTrigLevel())
#fg.close()