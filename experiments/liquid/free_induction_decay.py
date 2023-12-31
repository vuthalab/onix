import time

import numpy as np

from onix.data_tools import save_experiment_data
from onix.units import ureg

from onix.headers.pcie_digitizer.pcie_digitizer import Digitizer
from onix.headers.wavemeter.wavemeter import WM
from onix.headers.awg.M4i6622 import M4i6622

from onix.sequences.sequence import Sequence, Segment, AWGSinePulse, TTLPulses


def wavemeter_frequency():
    freq = wavemeter.read_frequency(5)
    if isinstance(freq, str):
        return -1
    return freq

wavemeter = WM()
m4i = M4i6622()

## experiment parameters
params = {
    "aom_channel": 2,
    "digitizer_channel": 0,
    "repeats": 10000,
    "segment_length": 100,

    "excitation": {
        "frequency": 80* ureg.MHz,
        "amplitude": 2000,
        "time": 0.5 * ureg.ms,
    },

    "coherence": {
        "frequency": 68* ureg.MHz,
        "amplitude": 800,
        "time": 1 * ureg.ms,
    },

    "yso": {
        "use": False,
        "eo_channel": 1,
        "frequency_excitation": 300 * ureg.MHz,
        "frequency_coherence": -275 * ureg.MHz,
        "eo_amplitude": 24000,
        "switch_ao_channel": 0,
        "switch_ao_frequency": 80 * ureg.MHz,
        "switch_ao_amplitude_excitation": 1500,
        "switch_ao_amplitude_coherence": 1000,
    }
}

## setup sequence
sequence = Sequence()
segment = Segment("excitation", duration=params["excitation"]["time"])
if params["yso"]["use"]:
    ao_pulse = AWGSinePulse(params["yso"]["switch_ao_frequency"], params["yso"]["switch_ao_amplitude_excitation"])
    segment.add_awg_function(params["yso"]["switch_ao_channel"], ao_pulse)
    eo_pulse = AWGSinePulse(params["yso"]["frequency_excitation"], params["yso"]["eo_amplitude"])
    segment.add_awg_function(params["yso"]["eo_channel"], eo_pulse)
else:
    ao_pulse = AWGSinePulse(params["excitation"]["frequency"], params["excitation"]["amplitude"])
    segment.add_awg_function(params["aom_channel"], ao_pulse)

ttl_gate = TTLPulses([[0, 4e-6]])
segment.add_ttl_function(params["digitizer_channel"], ttl_gate)
sequence.add_segment(segment)

segment = Segment("coherence", duration=params["coherence"]["time"])
if params["yso"]["use"]:
    ao_pulse = AWGSinePulse(params["yso"]["switch_ao_frequency"], params["yso"]["switch_ao_amplitude_coherence"])
    segment.add_awg_function(params["yso"]["switch_ao_channel"], ao_pulse)
    eo_pulse = AWGSinePulse(params["yso"]["frequency_coherence"], params["yso"]["eo_amplitude"])
    segment.add_awg_function(params["yso"]["eo_channel"], eo_pulse)
else:
    ao_pulse = AWGSinePulse(params["coherence"]["frequency"], params["coherence"]["amplitude"])
    segment.add_awg_function(params["aom_channel"], ao_pulse)
sequence.add_segment(segment)

measure_time = params["excitation"]["time"] + params["coherence"]["time"]

sequence.setup_sequence([("excitation", 1), ("coherence", 1)])

## setup the awg
m4i.setup_sequence(sequence)
sample_rate = int(1e8)
dg = Digitizer(False)
val = dg.configure_system(
    mode=1,
    sample_rate=sample_rate,
    segment_size=int(measure_time.to("s").magnitude * sample_rate),
    segment_count=params["segment_length"],
)

acq_params = dg.get_acquisition_parameters()
## take data
transmissions = None
for kk in range(int(params["repeats"] / params["segment_length"])):
    dg.arm_digitizer()
    time.sleep(0.1)
    for ll in range(params["segment_length"]):
        m4i.start_sequence()
        m4i.wait_for_sequence_complete()

    digitizer_data = dg.get_data()
    average_digitizer_data = np.array([np.average(digitizer_data[0], axis=0)])
    if transmissions is None:
        transmissions = average_digitizer_data
    else:
        transmissions = np.append(transmissions, average_digitizer_data, axis=0)

    print(np.shape(transmissions))

m4i.stop_sequence()

times = [kk / sample_rate for kk in range(len(transmissions[0]))]

## save data
header = {
    "params": params
}
data = {
    "times": times,
    "voltages": transmissions,
}
name = "Free Induction Decay"
data_id = save_experiment_data(name, data, header)
print(data_id)

## empty