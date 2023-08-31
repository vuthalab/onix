import time
import os
import contextlib
import io
import sys

import numpy as np

os.chdir("/home/onix/Documents/code")
os.environ["DATAFOLDER"] = "/home/onix/Documents/data"

from onix.data_tools import save_experiment_data
from onix.units import ureg

from onix.headers.digitizer import Digitizer
from onix.headers.wavemeter.wavemeter import WM
from onix.headers.awg.M4i6622 import M4i6622

from onix.sequences.sequence import Sequence, Segment, AWGSinePulse, TTLPulses

@contextlib.contextmanager
def nostdout():
    save_stdout = sys.stdout
    sys.stdout = io.StringIO()
    yield
    sys.stdout = save_stdout

def wavemeter_frequency():
    freq = wavemeter.read_frequency(5)
    if isinstance(freq, str):
        return -1
    return freq

wavemeter = WM()
try:
    dg = Digitizer("192.168.0.125")
    dg.list_errors()
except Exception:
    dg = Digitizer("192.168.0.125")

## experiment parameters
excitation_aom_channel = 0
excitation_aom_frequency = 78 * ureg.MHz
excitation_aom_amplitude = 2800
excitation_time = 5 * ureg.ms
excitation_delay = 10 * ureg.us

test_aom_channel = 0
test_aom_frequency = 78 * ureg.MHz
test_aom_amplitude = 300
test_time = 10 * ureg.us

pmt_gate_ttl_channel = 0  # also used to trigger the digitizer.
measurement_time = 10 * ureg.ms

time_between_repeat = 0.1  # s
repeats = 100
sampling_rate = 1e6

## setup sequence
sequence = Sequence(awg_channel_num=4, ttl_channels=[0])

segment_test = Segment("test")
offset = 100 * ureg.us
ttl_gate = TTLPulses([[0, offset.to("s").magnitude]])
segment_test.add_ttl_function(pmt_gate_ttl_channel, ttl_gate)
pulse_test = AWGSinePulse(
    frequency=test_aom_frequency,
    amplitude=test_aom_amplitude,
    start_time=offset*2+excitation_delay,
    end_time=offset*2+excitation_delay+test_time,
)
segment_test.add_awg_function(excitation_aom_channel, pulse_test)
segment_test._duration = segment_test.duration + offset.to("s").magnitude
sequence.add_segment("test", segment_test)

segment_excitation = Segment("excite")
pulse_excitation = AWGSinePulse(
    frequency=excitation_aom_frequency,
    amplitude=excitation_aom_amplitude,
    start_time=excitation_delay,
    end_time=excitation_delay + excitation_time,
)
segment_excitation.add_awg_function(excitation_aom_channel, pulse_excitation)
ttl_gate = TTLPulses([[0, (2 * excitation_delay + excitation_time).to("s").magnitude]])
segment_excitation.add_ttl_function(pmt_gate_ttl_channel, ttl_gate)
sequence.add_segment("excite", segment_excitation)

sequence.setup_sequence([("test", 1), ("excite", 1)])

## setup the awg
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

## setup the digitizer
params_dict = {
    "num_samples": int(measurement_time.to("s").magnitude * sampling_rate),
    "sampling_rate": int(sampling_rate),
    "ch1_voltage_range": 4,
    "ch2_voltage_range": 4,
    "trigger_channel": 0,
    "data_format": "float32",
    "coupling": "DC",
    "num_records": repeats + 1,
    "triggers_per_arm": repeats + 1,
}
dg.set_parameters(params_dict)
dg.configure()
dg.set_two_channel_waitForTrigger()

## take data
epoch_times = []
pmt_voltages = []

for kk in range(repeats + 1):
    m4i.startCard(False)
    epoch_times.append(time.time())
    time.sleep(sequence.total_duration + measurement_time.to("s").magnitude)
    time.sleep(time_between_repeat)
m4i.stop()

for kk in range(repeats + 1):
    V1, _ = dg.get_two_channel_waveform(kk + 1)
    if kk != 0:
        pmt_voltages.append(V1)  # first run data is always incorrect.

pmt_times = [kk / sampling_rate for kk in range(len(V1))]

## save data
data = {
    "pmt_times": pmt_times,
    "pmt_voltages": pmt_voltages,
    "epoch_times": epoch_times,
}
name = "Fluorescence Decay"
data_id = save_experiment_data(name, data)
print(data_id)
