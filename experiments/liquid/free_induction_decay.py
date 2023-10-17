import time

import numpy as np

from onix.data_tools import save_experiment_data
from onix.units import ureg

from onix.headers.digitizer import DigitizerVisa
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
dg = DigitizerVisa("192.168.0.125")

## experiment parameters
params = {
    "aom_channel": 2,
    "digitizer_channel": 0,
    "repeats": 10,

    "excitation": {
        "frequency": 80 * ureg.MHz,
        "amplitude": 2000,
        "time": 10 * ureg.ms,
    },

    "coherence": {
        "frequency": 76 * ureg.MHz,
        "amplitude": 1400,
        "time": 1 * ureg.ms,
    },
}

## setup sequence
sequence = Sequence()
segment = Segment("excitation", duration=params["excitation"]["time"])
ao_pulse = AWGSinePulse(params["excitation"]["frequency"], params["excitation"]["amplitude"])
segment.add_awg_function(params["aom_channel"], ao_pulse)
ao_pulse = AWGSinePulse(80e6, 250)
segment.add_awg_function(0, ao_pulse)
ao_pulse = AWGSinePulse(80e6, 2000)
segment.add_awg_function(3, ao_pulse)
ttl_gate = TTLPulses([[0, 4e-6]])
segment.add_ttl_function(params["digitizer_channel"], ttl_gate)
sequence.add_segment(segment)

segment = Segment("coherence", duration=params["coherence"]["time"])
ao_pulse = AWGSinePulse(params["coherence"]["frequency"], params["coherence"]["amplitude"])
segment.add_awg_function(params["aom_channel"], ao_pulse)
ao_pulse = AWGSinePulse(80e6, 250)
segment.add_awg_function(0, ao_pulse)
ao_pulse = AWGSinePulse(80e6, 2000)
segment.add_awg_function(3, ao_pulse)
sequence.add_segment(segment)

measure_time = params["excitation"]["time"] + params["coherence"]["time"]

sequence.setup_sequence([("excitation", 1), ("coherence", 1)])

## setup the awg and digitizer
m4i.setup_sequence(sequence)

sampling_rate = 2e7
dg.configure_acquisition(
    sample_rate=sampling_rate,
    samples_per_record=int(measure_time.to("s").magnitude * sampling_rate),
    num_records=params["repeats"],
)
dg.configure_channels(channels=[1], voltage_range=2)
dg.set_trigger_source_external()
dg.set_arm(triggers_per_arm=params["repeats"])

## take data

dg.initiate_data_acquisition()
time.sleep(0.5)
for kk in range(100):
    m4i.start_sequence()
    m4i.wait_for_sequence_complete()
for kk in range(params["repeats"]):
    m4i.start_sequence()
    m4i.wait_for_sequence_complete()
    time.sleep(0.01)
m4i.stop_sequence()

voltages = dg.get_waveforms([1], records=(1, params["repeats"]))[0]
times = [kk / sampling_rate for kk in range(len(voltages[0]))]

## save data
header = {
    "params": params
}
data = {
    "times": times,
    "voltages": voltages,
}
name = "Free Induction Decay"
data_id = save_experiment_data(name, data, header)
print(data_id)

## empty