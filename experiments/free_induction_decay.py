import time

import numpy as np

from onix.data_tools import save_experiment_data
from onix.units import ureg

from onix.headers.pcie_digitizer.pcie_digitizer import Digitizer
from onix.headers.wavemeter.wavemeter import WM
from onix.headers.awg.M4i6622 import M4i6622

from onix.sequences.free_induction_decay import FreeInductionDecay

def wavemeter_frequency():
    freq = wavemeter.read_frequency(5)
    if isinstance(freq, str):
        return -1
    return freq

wavemeter = WM()
m4i = M4i6622()

## experiment parameters
params = {
    "digitizer_channel": 0,
    "field_plate_channel": 1,
    "repeats": 100,

    "ao": {
        "channel": 0,
        "frequency": 80 * ureg.MHz,
        "amplitude": 2000,
        "detect_amplitude": 140,
    },

    "eo": {
        "channel": 1,
        "offset": 60 * ureg.MHz,
        "amplitude": 24000,
    },

    "detect_ao": {
        "channel": 3,
        "frequency": 80 * ureg.MHz,
        "amplitude": 0,
    },

    "burn": {
        "transition": "bb",
        "duration": 0.5 * ureg.s,
        "scan": 0.5 * ureg.MHz,
        "detuning": 0 * ureg.MHz,
    },

    "repop": {
        "transitions": ["ca", "ac"],
        "duration": 0.3 * ureg.s,
        "scan": 0.3 * ureg.MHz,
        "detuning": 0 * ureg.MHz,
    },

    "pump": {
        "transition": "bb",
        "time": 5 * ureg.ms,
        "ao_amplitude": 200,
        "repeats": 5,
    },

    "probe": {
        "time": 5 * ureg.ms,
        "ao_amplitude": 140,
        "detuning": 14.3 * ureg.MHz,
        "phase": 0,
    },
}

## setup the awg
sequence = FreeInductionDecay(
    ao_parameters=params["ao"],
    eo_parameters=params["eo"],
    detect_ao_parameters=params["detect_ao"],
    burn_parameters=params["burn"],
    repop_parameters=params["repop"],
    pump_parameters=params["pump"],
    probe_parameters=params["probe"],
    digitizer_channel=params["digitizer_channel"],
    field_plate_channel=params["field_plate_channel"],
)
sequence.setup_sequence()
m4i.setup_sequence(sequence)

sample_rate = 1e8
dg = Digitizer(False)
val = dg.configure_system(
    mode=1,
    sample_rate=sample_rate,
    segment_size=int(params["probe"]["time"].to("s").magnitude * sample_rate),
    segment_count=int(params["repeats"] * params["pump"]["repeats"]),
)

acq_params = dg.get_acquisition_parameters()

## take data
transmissions = None
dg.arm_digitizer()
time.sleep(0.1)
for kk in range(params["repeats"]):
    print(f"{kk / params['repeats'] * 100:.0f}%")
    m4i.start_sequence()
    m4i.wait_for_sequence_complete()

m4i.stop_sequence()
digitizer_data = dg.get_data()
if transmissions is None:
    transmissions = np.array(digitizer_data[0])
else:
    transmissions = np.append(transmissions, np.array(digitizer_data[0]), axis=0)

times = [kk / sample_rate for kk in range(len(transmissions[0]))]

## save data
header = {
    "params": params
}
data = {
    "times": times,
    "voltages": transmissions,
}
name = "Free Induction Decay Antihole"
data_id = save_experiment_data(name, data, header)
print(data_id)

## empty