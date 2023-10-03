import time
import os
import contextlib
import io
import sys

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

m4i = M4i6622()
wavemeter = WM()
dg = DigitizerVisa("192.168.0.125")

## experiment parameters
excitation_aom_channel = 2
excitation_aom_frequency = 82 * ureg.MHz
excitation_aom_amplitude = 2400
excitation_time = 10 * ureg.ms

probe_aom_amplitude = 2400
probe_aom_frequencies = np.linspace(80.5, 83.5, 30)
#np.random.shuffle(probe_aom_frequencies)
probe_aom_frequencies *= ureg.MHz
probe_time = 2 * ureg.us
probe_delay = 10 * ureg.us

digitizer_ttl_trigger = 0

repeats = 500
sampling_rate = 1e7

## setup sequence
def build_sequence(probe_aom_frequency):
    sequence = Sequence()

    segment_excitation = Segment("excite")
    pulse_excitation = AWGSinePulse(
        frequency=excitation_aom_frequency,
        amplitude=excitation_aom_amplitude,
        start_time=0,
        end_time=excitation_time,
    )
    segment_excitation.add_awg_function(excitation_aom_channel, pulse_excitation)
    sequence.add_segment(segment_excitation)

    segment_probe = Segment("probe")
    pulse_probe = AWGSinePulse(
        frequency=probe_aom_frequency,
        amplitude=probe_aom_amplitude,
        start_time=0,
        end_time=probe_time,
    )
    segment_probe.add_awg_function(excitation_aom_channel, pulse_probe)
    ttl_gate = TTLPulses([[0, 4e-6]])
    segment_probe.add_ttl_function(digitizer_ttl_trigger, ttl_gate)
    sequence.add_segment(segment_probe)

    segment_delay = Segment("delay", duration=probe_delay)
    sequence.add_segment(segment_delay)
    return sequence

## setup the digitizer
dg.configure_acquisition(
    sample_rate=sampling_rate,
    samples_per_record=int(sampling_rate * (probe_time + probe_delay).to("s").magnitude),
    num_records=repeats * 2,
)
dg.configure_channels(channels=[1, 2], voltage_range=10)
dg.set_trigger_source_external()
dg.set_arm(triggers_per_arm=repeats * 2)

## setup the awg, take data
data = {}
data["times"] = []
data["pre_excite_transmissions"] = []
data["post_excite_transmissions"] = []
data["pre_excite_reflections"] = []
data["post_excite_reflections"] = []

for probe_aom_frequency in probe_aom_frequencies:
    print(probe_aom_frequency)
    sequence = build_sequence(probe_aom_frequency)
    sequence.setup_sequence([("probe", 1), ("delay", 2), ("excite", 1), ("delay", 1), ("probe", 1), ("delay", 2)])
    m4i.setup_sequence(sequence)

    epoch_times = []
    pre_excite_transmissions = []
    post_excite_transmissions = []
    pre_excite_reflections = []
    post_excite_reflections = []

    dg.initiate_data_acquisition()
    time.sleep(0.1)
    for kk in range(repeats):
        m4i.start_sequence()
        epoch_times.append(time.time())
        m4i.wait_for_sequence_complete()
        time.sleep(0.01)
    time.sleep(0.1)

    voltages = dg.get_waveforms([1, 2], records=(1, repeats * 2))
    for kk in range(len(voltages[0])):
        if kk % 2 == 0:
            pre_excite_transmissions.append(voltages[0][kk])
            pre_excite_reflections.append(voltages[1][kk])
        else:
            post_excite_transmissions.append(voltages[0][kk])
            post_excite_reflections.append(voltages[1][kk])

    data["pre_excite_transmissions"].append(pre_excite_transmissions)
    data["pre_excite_reflections"].append(pre_excite_reflections)
    data["post_excite_transmissions"].append(post_excite_transmissions)
    data["post_excite_reflections"].append(post_excite_reflections)
    data["times"] = [kk / sampling_rate for kk in range(len(pre_excite_transmissions[0]))]

## save data
headers = {
    "params": {
        "excitation_aom_frequency": excitation_aom_frequency,
        "excitation_aom_amplitude": excitation_aom_amplitude,
        "excitation_time": excitation_time,
        "probe_aom_amplitude": probe_aom_amplitude,
        "probe_time": probe_time,
        "probe_delay": probe_delay,
        "probe_aom_frequencies": probe_aom_frequencies,
        "repeats": repeats,
        "sampling_rate": sampling_rate,
    }
}
name = "Hole burning spectral"
data_id = save_experiment_data(name, data, headers)
print(data_id)

## empty