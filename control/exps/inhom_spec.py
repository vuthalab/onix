import numpy as np
import time
from onix.control.devices import m4i, dg
from onix.control.awg_maps import get_awg_channel_from_name, get_ttl_channel_from_name
from onix.control.exps.shared import update_parameters_from_shared
from onix.units import ureg
from onix.headers.wavemeter.wavemeter import WM
from onix.data_tools import save_experiment_data

parameters = update_parameters_from_shared({})


def set_optical(amplitude, frequency = None):
    if frequency is None:
        frequency = parameters["ao"]["frequency_ac"]
    m4i.set_sine_output(get_awg_channel_from_name(parameters["ao"]["channel_name"]), frequency, amplitude)


def set_shutter(state: bool):
    m4i.set_ttl_output(get_ttl_channel_from_name(parameters["shutter"]["channel_name"]), state)


##
wm = WM()
dg.set_acquisition_config(
    num_channels=2,
    sample_rate=10000,
    segment_size=1000,
    segment_count=1,
)
dg.set_channel_config(channel=1, range=2)
dg.set_channel_config(channel=2, range=2)
dg.set_trigger_source_software()
dg.write_configs_to_device()
m4i.start_sine_outputs()
for kk in np.linspace(-5e3, 5e3, 20):
    set_optical(int(0.15 * ureg.V / (2.5 * ureg.V) * 32768), parameters["ao"]["frequency_ac"].to("Hz").magnitude + kk)
    time.sleep(1)
set_optical(int(0.015 * ureg.V / (2.5 * ureg.V) * 32768))
set_shutter(True)
V1 = []
V2 = []
f = []
try:
    input("Hole burning done. Enter anything to start the spectroscopy: ")
    print("started")
    while True:
        time.sleep(0.5)
        dg.start_capture()
        f.append(wm.read_frequency(5))
        dg.wait_for_data_ready(1)
        _, data = dg.get_data()
        V1.append(np.average(data[0]))
        V2.append(np.average(data[1]))
except KeyboardInterrupt as e:
    set_shutter(False)
    m4i.stop_sine_outputs()
    print("stopped")

print(save_experiment_data("Inhomogeneous Spectroscopy", {"V_transmission": V1, "V_monitor": V2, "wavemeter_frequency": f}, headers = {"voltage": 1000}, edf_number=None))