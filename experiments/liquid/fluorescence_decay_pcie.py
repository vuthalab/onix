import time
import os
import numpy as np

# os.chdir("/home/onix/Documents/code")
# os.environ["DATAFOLDER"] = "/home/onix/Documents/data"

#os.environ["DATAFOLDER"] = "/home/icarus/Documents/data"

from onix.data_tools import save_experiment_data
from onix.units import ureg

from onix.headers.pcie_digitizer.pcie_digitizer import Digitizer
from onix.headers.wavemeter.wavemeter import WM
from onix.headers.awg.M4i6622 import M4i6622
from onix.sequences.sequence import Sequence, Segment, AWGSinePulse, TTLPulses

# dg = DigitizerVisa("192.168.0.125")
# dg_channels = [1, 2]

import contextlib
import io
import sys

try:
    m4i  # type: ignore
    print("m4i is already defined.")
except Exception:
    try:
        m4i = M4i6622()
    except Exception as e:
        m4i = None
        print("m4i is not defined with error:")
        print(traceback.format_exc())

try:
    wm # type: ignore
    print("WM is already defined")
except Exception:
    try:
        wm = WM()
    except Exception as e:
        wm = None
        print("wm is not defined with error:")
        print(traceback.format_exc())


def wavemeter_frequency():
    freq = wm.read_frequency(5)
    if isinstance(freq, str):
        return -1
    return freq


## experiment parameters
excitation_aom_channel = 1
excitation_aom_frequency = 78 * ureg.MHz
excitation_aom_amplitude = 2800
excitation_time = 5 * ureg.ms
excitation_delay = 10 * ureg.us

test_aom_channel = 1
test_aom_frequency = 78 * ureg.MHz
test_aom_amplitude = 500
test_time = 10 * ureg.us

pmt_gate_ttl_channel = 2  # also used to trigger the digitizer.
measurement_time = 8 * ureg.ms + excitation_time

repeats = 10
time_between_repeat = measurement_time.to("s").magnitude
sampling_rate = 1e6

## setup sequence
sequence = Sequence()

segment_test = Segment("test")
offset = 100 * ureg.us
ttl_gate = TTLPulses([[0, offset]]) # ttl 0-100us
segment_test.add_ttl_function(pmt_gate_ttl_channel, ttl_gate)
pulse_test = AWGSinePulse( # awg 210 us - 220 us
    frequency=test_aom_frequency,
    amplitude=test_aom_amplitude,
    start_time=offset*2+excitation_delay,
    end_time=offset*2+excitation_delay+test_time,
)
segment_test.add_awg_function(excitation_aom_channel, pulse_test)
segment_test._duration = segment_test.duration + offset
sequence.add_segment(segment_test)

segment_excitation = Segment("excite")
pulse_excitation = AWGSinePulse( # awg 10 us - 5ms
    frequency=excitation_aom_frequency,
    amplitude=excitation_aom_amplitude,
    start_time=excitation_delay,
    end_time=excitation_delay+excitation_time,
) # ttl 5 ms + 20us - 12 ms + 20us
segment_excitation.add_awg_function(excitation_aom_channel, pulse_excitation)
ttl_gate = TTLPulses([[2 * excitation_delay + excitation_time, 2 * excitation_delay + measurement_time]])
segment_excitation.add_ttl_function(pmt_gate_ttl_channel, ttl_gate)
sequence.add_segment(segment_excitation)

sequence.setup_sequence([("test", 1), ("excite", 1)])

## setup the awg and digitizer
m4i.setup_sequence(sequence)

# dg.configure_acquisition(
#     sample_rate=sampling_rate,
#     samples_per_record=int(measurement_time.to("s").magnitude * sampling_rate),
#     num_records=repeats,
# )
# dg.configure_channels(channels=[1], voltage_range=2)
# dg.set_trigger_source_external()
# dg.set_arm(triggers_per_arm=repeats)

try:
    dg
    print("dg is already defined.")
except Exception:
    dg = Digitizer()


duration = measurement_time.to("s").magnitude
dg.set_acquisition_config(
    num_channels=1,
    sample_rate=sampling_rate,
    segment_size=int(duration * sampling_rate),
    segment_count=1,
)

dg.set_channel_config(channel=1, range=5, high_impedance=False)
dg.set_trigger_source_edge()
dg.write_configs_to_device()

## take data
epoch_times = []
pmt_voltages = []
pmt_times = []

# dg.initiate_data_acquisition()
for kk in range(repeats):
    dg.start_capture()
    time.sleep(0.5)
    m4i.start_sequence()
    epoch_times.append(time.time())
    m4i.wait_for_sequence_complete()
    time.sleep(time_between_repeat)
    m4i.stop_sequence()
    timeout = 1
    dg.wait_for_data_ready(timeout)
    sample_rate, digitizer_data = dg.get_data()
    pmt_voltages.append(digitizer_data[0][0])
# pmt_voltages = np.average(pmt_voltages, axis=0)
pmt_times = [kk / sample_rate for kk in range(len(pmt_voltages[0]))]

## save data
header = {
    "excitation_aom_channel": excitation_aom_channel,
    "excitation_aom_frequency": excitation_aom_frequency,
    "excitation_aom_amplitude": excitation_aom_amplitude,
    "excitation_time": excitation_time,
    "excitation_delay": excitation_delay,
    "test_aom_channel": test_aom_channel,
    "test_aom_frequency": test_aom_frequency,
    "test_aom_amplitude": test_aom_amplitude,
    "pmt_gate_ttl_channel": pmt_gate_ttl_channel,
    "measurement_time": measurement_time,
    "repeats": repeats,
    "time_between_repeat": time_between_repeat,
    "sampling_rate": sample_rate,
}
data = {
    "pmt_times": pmt_times,
    "pmt_voltages": pmt_voltages,
    "epoch_times": epoch_times,
}
name = "Fluorescence Decay"
data_id = save_experiment_data(name, data, header)
print(data_id)

##