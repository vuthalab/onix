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

wavemeter = WM()
dg = DigitizerVisa("192.168.0.125")

## experiment parameters
excitation_aom_channel = 2
excitation_aom_frequency = 78 * ureg.MHz
excitation_aom_amplitude = 2800
excitation_time = 2 * ureg.ms

probe_aom_amplitude = 500
probe_time = 5 * ureg.us
probe_delay_step_size = 5 * ureg.us
probe_delay_steps = np.arange(1, 40, 2)
np.random.shuffle(probe_delay_steps)

digitizer_ttl_trigger = 0

repeats = 20
sampling_rate = 1e7

## setup sequence
sequence = Sequence(awg_channel_num=4, ttl_channels=[digitizer_ttl_trigger])

segment_excitation = Segment("excite")
pulse_excitation = AWGSinePulse(
    frequency=excitation_aom_frequency,
    amplitude=excitation_aom_amplitude,
    start_time=0,
    end_time=excitation_time,
)
segment_excitation.add_awg_function(excitation_aom_channel, pulse_excitation)
sequence.add_segment("excite", segment_excitation)

segment_probe = Segment("probe")
pulse_probe = AWGSinePulse(
    frequency=excitation_aom_frequency,
    amplitude=probe_aom_amplitude,
    start_time=0,
    end_time=probe_time,
)
segment_probe.add_awg_function(excitation_aom_channel, pulse_probe)
ttl_gate = TTLPulses([[0, 4e-6]])
segment_probe.add_ttl_function(digitizer_ttl_trigger, ttl_gate)
sequence.add_segment("probe", segment_probe)

segment_delay = Segment("delay", duration=probe_delay_step_size)
sequence.add_segment("delay", segment_delay)

## setup the digitizer
dg.configure_acquisition(
    sample_rate=sampling_rate,
    samples_per_record=int(sampling_rate * (probe_time + probe_delay_step_size).to("s").magnitude),
    num_records=repeats * 2,

)
dg.configure_channels(channels=[1, 2], voltage_range=4)
dg.set_trigger_source_external()
dg.set_arm(triggers_per_arm=repeats * 2)

## setup the awg, take data
data = {}
data["probe_delay_steps"] = []
data["times"] = []
data["pre_excite_transmissions"] = []
data["post_excite_transmissions"] = []
data["pre_excite_reflections"] = []
data["post_excite_reflections"] = []

for delay_step in probe_delay_steps:
    print(delay_step)
    data["probe_delay_steps"].append(delay_step)
    sequence.setup_sequence([("probe", 1), ("delay", 2), ("excite", 1), ("delay", delay_step), ("probe", 1), ("delay", 2)])
    m4i = M4i6622(
        channelNum=4,
        sequenceReplay=True,
        loop_list=sequence.segment_loops,
        next=sequence.segment_next,
        conditions=sequence.segment_conditions,
        initialStep=0,
        segTimes=sequence.segment_durations,
        ttlOutOn=sequence.ttl_out_on,
        ttlOutChannel=sequence._ttl_channels,
        verbose=True,
    )
    m4i.setSoftwareBuffer()
    m4i.configSequenceReplay(
        segFunctions=sequence.segment_awg_functions,
        steps=sequence.segment_steps,
        ttlFunctionList=sequence.segment_ttl_functions,
    )

    epoch_times = []
    pre_excite_transmissions = []
    post_excite_transmissions = []
    pre_excite_reflections = []
    post_excite_reflections = []

    dg.initiate_data_acquisition()
    time.sleep(0.2)
    for kk in range(repeats):
        m4i.startCard(False)
        epoch_times.append(time.time())
        time.sleep(sequence.total_duration)
        time.sleep(0.1)
    m4i.stop()

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
        "excitation_aom_amplitude": excitation_aom_amplitude,
        "excitation_time": excitation_time,
        "probe_aom_amplitude": probe_aom_amplitude,
        "probe_time": probe_time,
        "probe_delay_step_size": probe_delay_step_size,
        "probe_delay_steps": probe_delay_steps,
        "repeats": repeats,
        "sampling_rate": sampling_rate,
    }
}
name = "Hole burning temporal"
data_id = save_experiment_data(name, data, headers)
print(data_id)
