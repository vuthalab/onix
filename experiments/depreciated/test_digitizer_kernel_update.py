from onix.headers.pcie_digitizer.pcie_digitizer import Digitizer
from onix.headers.awg.M4i6622 import M4i6622
from onix.headers.wavemeter.wavemeter import WM

import numpy as np
import time
import matplotlib.pyplot as plt

wm = WM()
m4i = M4i6622()
dg = Digitizer()


run_time = 1e-3
sample_rate = 1e8

dg.set_acquisition_config(
        num_channels=1,
        sample_rate=sample_rate,
        segment_size=int(run_time * sample_rate),
        segment_count=1
    )

for channel_no in [1]:
    dg.set_channel_config(channel=channel_no, range=1, ac_coupled=False)

dg.set_trigger_source_software()
dg.write_configs_to_device()
m4i.set_sine_output(1, 80e6, 250)
m4i.start_sine_outputs()


freqs = []
voltages = []
try:
    while True:
        print("collecting")
        dg.start_capture()
        dg.wait_for_data_ready(1)
        time.sleep(0.1)
        sample_rate, digitizer_data = dg.get_data()
        voltages.append(np.mean(digitizer_data[0][0]))
        freq = wm.read_frequency(5)
        freqs.append(freq)
except KeyboardInterrupt: ############ CTRL + I to interrupt in pyzo
    pass

m4i.stop_sine_outputs()
plt.scatter(np.array(freqs)-516847.603, voltages, s = 1)
plt.xlabel("Frequency (GHz)")
plt.ylabel("Transmission (V)")
plt.show()


