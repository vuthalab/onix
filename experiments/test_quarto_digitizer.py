import time
import os
import numpy as np

from onix.data_tools import save_experiment_data
from onix.units import ureg

from onix.experiments.shared import m4i, run_sequence
from onix.sequences.sequence import Sequence, Segment, AWGSinePulse, TTLPulses


## setup sequence
sequence = Sequence()

segment_
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
ttl_gate = TTLPulses([[0, 2 * excitation_delay + excitation_time]])
segment_excitation.add_ttl_function(pmt_gate_ttl_channel, ttl_gate)
sequence.add_segment(segment_excitation)

sequence.setup_sequence([("test", 1), ("excite", 1)])

## setup the awg and digitizer
m4i.setup_sequence(sequence)

duration = measurement_time.to("s").magnitude
dg.set_acquisition_config(
    num_channels=1,
    sample_rate=sampling_rate,
    segment_size=int(duration * sampling_rate),
    segment_count=repeats,
)

dg.set_channel_config(channel=1, range=5, high_impedance=False)
dg.set_trigger_source_edge()
dg.write_configs_to_device()

## take data
epoch_times = []
pmt_voltages = []
pmt_times = []

# dg.initiate_data_acquisition()
dg.start_capture()

for kk in range(repeats):
    time.sleep(0.1)
    m4i.start_sequence()
    epoch_times.append(time.time())
    m4i.wait_for_sequence_complete()
    time.sleep(time_between_repeat)

m4i.stop_sequence()
timeout = 1
dg.wait_for_data_ready(timeout)
sample_rate, digitizer_data = dg.get_data()
pmt_voltages = digitizer_data[0]
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
    "frequency": frequency,
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
