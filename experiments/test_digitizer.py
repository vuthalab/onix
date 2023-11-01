import numpy as np
import time
import matplotlib.pyplot as plt

from onix.headers.pcie_digitizer.pcie_digitizer import Digitizer
from onix.headers.awg.M4i6622 import M4i6622

m4i = M4i6622()
m4i.start_sine_outputs()

###
def set_channel_output(amplitude_V):
    m4i.set_sine_output(3, 1e6, amplitude_V / 2.5 * 32768)

def trigger():
    m4i.set_ttl_output(0, True)
    m4i.set_ttl_output(0, False)


dg = Digitizer(False)
val = dg.configure_system(
    mode=1,
    sample_rate=int(1e8),
    segment_size=4080,
    segment_count=1,
)

"""
val = dg.configure_trigger(
    edge = 'falling',
    level = 40,
    source = 'software',
    range = 5,
    impedance = 50,
    coupling = 'AC'
)
"""
val = dg.configure_trigger(source = 'software')

def test_sequence():
    set_channel_output(0.5)
    dg.arm_digitizer()
    time.sleep(1)
    data = dg.get_data()
    set_channel_output(0)
    return data

