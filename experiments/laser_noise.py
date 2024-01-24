import matplotlib.pyplot as plt
import numpy as np
import time
from onix.data_tools import save_experiment_data
from onix.analysis.debug.laser_linewidth import LaserLinewidth
from onix.headers.pcie_digitizer.pcie_digitizer import Digitizer
import matplotlib.pyplot as plt


try:
    dg
    print("dg is already defined.")
except Exception:
    dg = Digitizer()


## setup
set_sample_rate = 100e6
duration = 0.1
dg.set_acquisition_config(
    num_channels=1,
    sample_rate=set_sample_rate,
    segment_size=int(duration * set_sample_rate),
    segment_count=1,
)
dg.set_channel_config(channel=1, range=2)
#dg.set_channel_config(channel=2, range=0.5)
dg.set_trigger_source_software()
dg.write_configs_to_device()


## take data
params = {
    "p": 0.1,
    "i": 1000,
    "d": 0,
    "error_offset": 1.35,
    "output_offset": 0.0,
    "integral_limit": 5,
    "repeats": 10,
}


voltages = []
for kk in range(params["repeats"]):
    dg.start_capture()
    time.sleep(duration)
    timeout = 0.1
    dg.wait_for_data_ready(timeout)
    sample_rate, data = dg.get_data()
    voltages.append(data[0][0])

max_point_per_decade = 100
discriminator_slope = 1  # unused
noise = LaserLinewidth(voltages, 1 / sample_rate, discriminator_slope, max_point_per_decade)
f = noise.f
laser_noise = np.sqrt(noise.W_V)
fractional_noise = laser_noise / np.average(voltages)

data = {
    "f": f,
    "noise": laser_noise,
    "fractional_noise": fractional_noise,
}
headers = {
    "params": params,
}

name = "Laser Noise"
data_id = save_experiment_data(name, data, headers)
print(data_id)

##