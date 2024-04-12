import time

from onix.data_tools import save_experiment_data
from onix.units import ureg

from onix.experiments.shared import m4i
from onix.sequences.sequence import Sequence, Segment, AWGSinePulse, TTLPulses
from onix.headers.quarto_digitizer import Quarto

import matplotlib.pyplot as plt
import numpy as np

try:
    q
except Exception:
    q = Quarto("/dev/ttyACM6")

## params
params = {
    "awg_channel": 4,
    "ttl_channel": 3,
    "frequency": 100 * ureg.kHz,
    "amplitude": 20000,
    "duration": 20 * ureg.us,
    "delay_time": 4 * ureg.us,
    "trigger_offset": 0 * ureg.us,
    "trigger_duration": 1 * ureg.us,
    "repeats": 10,
}

## setup sequence
sequence = Sequence()

segment = Segment("main")
segment.add_ttl_function(params["ttl_channel"], TTLPulses([[params["trigger_offset"], params["trigger_offset"] + params["trigger_duration"]]]))
segment.add_awg_function(params["awg_channel"], AWGSinePulse(params["frequency"], params["amplitude"], end_time=params["duration"]))
segment._duration = segment.duration + params["delay_time"]
sequence.add_segment(segment)
sequence.setup_sequence([("main", params["repeats"])])

## setup the awg and digitizer
m4i.setup_sequence(sequence)
sample_size = int(params["duration"].to("us").magnitude)
sample_count = int(params["repeats"])
q.setup(sample_size, sample_count)

## take data
q.start()
m4i.start_sequence()
m4i.wait_for_sequence_complete()
m4i.stop_sequence()
q.stop()
data = q.data().reshape((sample_count, sample_size))
times = np.arange(sample_size)

## plot data
for kk, d in enumerate(data):
    plt.plot(times - kk * 0.013, data[kk])
plt.ylabel("Voltage (V)")
plt.xlabel("Time (us)")
plt.show()

## save data
header = {
    "params": params,
}
data = {
    "data": data,
}
name = "Quarto digitizer test"
#data_id = save_experiment_data(name, data, header)
#print(data_id)

##
