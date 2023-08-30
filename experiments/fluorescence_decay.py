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
excitation_aom_frequency = 80 * ureg.MHz
excitation_aom_amplitude = 2000
excitation_time = 0.1 * ureg.s

measurement_delay = 10 * ureg.us
pmt_gate_ttl_channel = 0  # also used to trigger the digitizer.
measurement_time = 0.1 * ureg.s  # with ttl trigger, something happens after ~87 ms. Readings on the two channels flip.

time_between_repeat = 1  # s
repeats = 1
sampling_rate = 1e5

## setup sequence
sequence = Sequence(awg_channel_num=4, ttl_channels=[0])

segment_excitation = Segment("excite")
pulse_excitation = AWGSinePulse(
    frequency=excitation_aom_frequency,
    amplitude=excitation_aom_amplitude,
    start_time=0,
    end_time=excitation_time,
)
segment_excitation.add_awg_function(excitation_aom_channel, pulse_excitation)
sequence.add_segment("excite", segment_excitation)

segment_measure = Segment("measure")
ttl_measure = TTLPulses([[measurement_delay.to("s").magnitude, (measurement_delay + measurement_time).to("s").magnitude]])
segment_measure.add_ttl_function(pmt_gate_ttl_channel, ttl_measure)
sequence.add_segment("measure", segment_measure)

sequence.setup_sequence([("excite", 1), ("measure", 1)])

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
    verbose=True
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
    "ch1_voltage_range": 10,
    "ch2_voltage_range": 10,
    "trigger_channel": 0,
    "data_format": "float32",
    "coupling": "DC",
    "num_records": repeats,
    "triggers_per_arm": repeats,
}
dg.set_parameters(params_dict)
dg.configure()
dg.set_two_channel_waitForTrigger()

## take data
frequency_GHz = []
epoch_times = []
pmt_voltages = []

for kk in range(repeats):
    m4i.startCard(False)
    time.sleep(sequence.total_duration)
    frequency_GHz.append(wavemeter_frequency())
    epoch_times.append(time.time())
    V1, _ = dg.get_two_channel_waveform()
    pmt_voltages.append(V1)
    time.sleep(time_between_repeat)

m4i.stop()
pmt_times = [kk / sampling_rate for kk in range(len(V1))]

## save data
data = {
    "pmt_times": pmt_times,
    "pmt_voltages": pmt_voltages,
    "epoch_times": epoch_times,
    "frequency_GHz": frequency_GHz,
}
name = "Fluorescence Decay"
data_id = save_experiment_data(name, data)
print(data_id)
