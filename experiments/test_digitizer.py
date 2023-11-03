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
    mode=0,
    sample_rate=int(1e8),
    segment_size=4090,
    segment_count=1,
    voltage_range = 1000,
)


val = dg.configure_trigger(
    edge = 'falling',
    level = 40,
    source = 'external',
    range = 3,
    impedance = 50,
)

def test_sequence():
    dg.arm_digitizer()
    time.sleep(1)
    trigger()
    set_channel_output(2.0)
    time.sleep(1)
    digitizer_data = dg.get_data()
    set_channel_output(0)
    data = np.array(digitizer_data[0]).flatten().tolist()
    data = [2*i/(1.54150390625 * dg.get_channel_parameters(1)['InputRange'] * 1e-3) for i in data]
    print(max(data))
    return data



