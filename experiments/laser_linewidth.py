import matplotlib.pyplot as plt
import numpy as np
import time
from onix.data_tools import save_experiment_data

from onix.headers.wavemeter.wavemeter import WM
from onix.headers.quarto import Quarto
from onix.headers.digitizer import DigitizerVisa
import matplotlib.pyplot as plt

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
    "source": "agilent",  # "quatro", "agilent"
}

## Get error signal data
V_errs = []
N_avgs = params["n_avg"]
if params["source"] == "quatro":
    qu = Quarto()
    resolution = 2e-6
    for i in range(N_avgs):
        V_errs.append(qu.get_errdata())
        time.sleep(1)
elif params["source"] == "agilent":
    dg = DigitizerVisa("192.168.0.125")
    duration = 0.1
    sample_rate = 10e6
    resolution = 1 / sample_rate
    samples = int(duration * sample_rate)
    dg.configure_acquisition(
        sample_rate=sample_rate,
        samples_per_record=samples,
        num_records=1,
    )
    dg.configure_channels([1], voltage_range=0.2)
    dg.set_trigger_source_immediate()
    dg.set_arm(triggers_per_arm=1)
    dg.initiate_data_acquisition()
    for i in range(N_avgs):
        V_errs.append(dg.get_waveforms([1], 1)[0][0])
        time.sleep(duration)

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
