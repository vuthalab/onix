import time

import numpy as np
from onix.data_tools import save_experiment_data
from onix.units import ureg

from onix.headers.digitizer import DigitizerVisa
from onix.headers.awg.M4i6622 import M4i6622
from onix.sequences.apd_saturation import APDSaturation

m4i = M4i6622()
dg = DigitizerVisa("192.168.0.125")

## parameters

params = {
    "digitizer_channel": 0,
    "repeats": 3,
    "saturation_time": 0.001 * ureg.s,
    "detection_time": 1 * ureg.s,

    "ao": {
        "channel": 0,
        "frequency": 80 * ureg.MHz,
        "amplitude": 2000,
        "detect_amplitude": 140,
    },

    "detect_ao": {
        "channel": 3,
        "frequency": 80 * ureg.MHz,
        "amplitude": 2000,
    },
}

## setup sequence
sequence = APDSaturation(
    ao_parameters=params["ao"],
    detect_ao_parameters=params["detect_ao"],
    digitizer_channel=params["digitizer_channel"],
    saturation_time=params["saturation_time"],
    detection_time=params["detection_time"],
)
sequence.setup_sequence()

## setup the awg and digitizer
m4i.setup_sequence(sequence)

sample_rate = 1e4
dg.configure_acquisition(
    sample_rate=sample_rate,
    samples_per_record=int(sequence.detect_time.to("s").magnitude * sample_rate),
    num_records=1,
)
dg.configure_channels(channels=[1], voltage_range=2)
dg.set_trigger_source_external()
dg.set_arm(triggers_per_arm=1)

## take data
epoch_times = []
transmissions = []

for kk in range(params["repeats"]):
    dg.initiate_data_acquisition()
    time.sleep(0.1)
    m4i.start_sequence()
    epoch_times.append(time.time())
    m4i.wait_for_sequence_complete()
    time.sleep(params["detection_time"].to("s").magnitude)
    time.sleep(0.1)
    voltages = dg.get_waveforms([1], records=1)
    transmissions.append(voltages[0][0])
m4i.stop_sequence()

photodiode_times = [kk / sample_rate for kk in range(len(transmissions[0]))]

## plot
#plt.plot(photodiode_times, np.transpose(photodiode_voltages)); plt.legend(); plt.show();

## save data
data = {
    "times": photodiode_times,
    "transmissions": transmissions,
    "epoch_times": epoch_times,
}
headers = {
    "params": params,
}
name = "APD Saturation"
data_id = save_experiment_data(name, data, headers)
print(data_id)

## empty