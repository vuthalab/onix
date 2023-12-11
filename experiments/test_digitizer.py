import numpy as np
import time
import matplotlib.pyplot as plt

from onix.headers.pcie_digitizer.pcie_digitizer import Digitizer
import onix.headers.pcie_digitizer.GageSupport as gs

from onix.headers.awg.M4i6622 import M4i6622

m4i = M4i6622('/dev/spcm1')
m4i.start_sine_outputs()

#m4i.set_sine_output(1, 1e5, 1 / 2.5 * 32768)
#m4i.stop_sine_outputs()

#m4i1 = M4i6622(address="/dev/spcm1")
#m4i1.start_sine_outputs()
#m4i1.set_sine_output(1, 1e5, 1 / 2.5 * 32768)
#m4i1.stop_sine_outputs()

###
def set_channel_output(amplitude_V):
    m4i.set_sine_output(1, 1e5, amplitude_V / 2.5 * 32768)

def trigger():
    m4i.set_ttl_output(0, True)
    time.sleep(0.01)
    m4i.set_ttl_output(0, False)


dg = Digitizer(False)

val = dg.configure_system(
    mode=1,
    sample_rate = int(1e6),
    segment_size = 400,
    voltage_range = 1
)

val = dg.configure_trigger(
    source = 'external',
    edge = 'rising',
    level = 30,
)


def test_sequence():
    time.sleep(1)
    set_channel_output(0.25)
    dg.arm_digitizer() #120us to start taking data
    trigger()
    time.sleep(1)
    digitizer_data = dg.get_data()
    set_channel_output(0)
    return digitizer_data


##

data = np.array(test_sequence()[0][0])

plt.plot(data)
plt.show()

##
filename = "/home/onix/Documents/code/onix/headers/pcie_digitizer/digitizerParameters.ini"
acq, sts = gs.LoadChannelConfiguration(dg._handle, filename)


