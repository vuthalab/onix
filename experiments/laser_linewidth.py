import matplotlib.pyplot as plt
import numpy as np
import time
from onix.data_tools import save_experiment_data

from onix.headers.wavemeter.wavemeter import WM
from onix.headers.quarto_frequency_lock import Quarto
from onix.headers.pcie_digitizer.pcie_digitizer import Digitizer
import matplotlib.pyplot as plt
from onix.headers.awg.M4i6622 import M4i6622
from onix.analysis.laser_linewidth import LaserLinewidth
m4i = M4i6622()


discriminator_slope = 1
laser = LaserLinewidth(1000, 2e-6, discriminator_slope, None)

wavemeter = WM()

def wavemeter_frequency():
    freq = wavemeter.read_frequency(params["wm_channel"])
    if isinstance(freq, str):
        return -1
    return freq

## Parameters
params = {
    "wm_channel": 5,
    "n_avg" : 10,
    "source": "quarto"
}

## Get error signal data
V_errs = []
N_avgs = params["n_avg"]
if params["source"] == "quatro":
    q = Quarto()
    resolution = 2e-6 #quantization noise is 1e-7
    for i in range(N_avgs):
        err_data = q.get_all_data["error"]
        V_errs.append(err_data)
        laser.add_data(err_data)
        time.sleep(1)
    print("Laser Linewidth is {laser.linewidth} Hz")

def trigger():
    m4i.set_ttl_output(0, True)
    time.sleep(0.01)
    m4i.set_ttl_output(0, False)

if params["source"] == "gage":
    sample_rate = int(1e8)

    resolution = 1/sample_rate

    duration = 0.1
    dg = Digitizer(False)
    val = dg.configure_system(
        mode=1,
        sample_rate= sample_rate,
        segment_size= int(duration * sample_rate),
        segment_count= N_avgs,
        voltage_range = 2000
    )

    val = dg.configure_trigger(
        edge = 'rising',
        level = 30,
        source = 'external',
        coupling = 1,
        range = 10000
    )

    dg.arm_digitizer()

    m4i.set_sine_output(0, 80e6, 500)
    m4i.start_sine_outputs()
    time.sleep(0.1)

    for i in range(N_avgs):
        trigger()
        time.sleep(1)

    data = dg.get_data()

    m4i.stop_sine_outputs()

    V_errs = data[0]

## Save Data
data = {
    "V_errs": V_errs,
}
headers = {
    "params": params,
    "wavemeter_frequency": wavemeter_frequency(),
    "resolution" : resolution,
}

name = "Laserlock Error"
data_id = save_experiment_data(name, data, headers)
print(data_id)


