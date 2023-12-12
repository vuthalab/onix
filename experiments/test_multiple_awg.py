import numpy as np
import time
import matplotlib.pyplot as plt

from onix.units import ureg
from onix.sequences.sequence import Sequence, Segment, AWGSinePulse, TTLPulses
from onix.headers.pcie_digitizer.pcie_digitizer import Digitizer
from onix.headers.awg.M4i6622 import M4i6622

m4i = M4i6622(['/dev/spcm0', '/dev/spcm1'])

##
params = {
    "ch1": 1,
    "ch2": 5,
    "digitizer_channel": 2,

    "pulse1": {
        "frequency1": 8* ureg.MHz,
        "amplitude1": 2,
        "frequency2": 3* ureg.MHz,
        "amplitude2": 1,
        "time": 0.5 * ureg.ms,
    },

    "pulse2": {
        "frequency1": 5* ureg.MHz,
        "amplitude1": 0.75,
        "frequency2": 7* ureg.MHz,
        "amplitude2": 1.5,
        "time": 1 * ureg.ms,
    },
}


##
sequence = Sequence()

segment = Segment("pulse1", duration=params["pulse1"]["time"])

ch1_pulse1 = AWGSinePulse(params["pulse1"]["frequency1"], params["pulse1"]["amplitude1"]/2.5 * 32768)
segment.add_awg_function(params["ch1"], ch1_pulse1)

ch2_pulse1 = AWGSinePulse(params["pulse1"]["frequency2"], params["pulse1"]["amplitude2"]/2.5 * 32768)
segment.add_awg_function(params["ch2"], ch2_pulse1)

ttl_gate = TTLPulses([[0, 4e-4]])
segment.add_ttl_function(params["digitizer_channel"], ttl_gate)

sequence.add_segment(segment)

segment = Segment("pulse2", duration=params["pulse2"]["time"])

ch1_pulse2 = AWGSinePulse(params["pulse2"]["frequency1"], params["pulse2"]["amplitude1"]/2.5 * 32768)
segment.add_awg_function(params["ch1"], ch1_pulse2)

ch2_pulse2 = AWGSinePulse(params["pulse2"]["frequency2"], params["pulse2"]["amplitude2"]/2.5 * 32768)
segment.add_awg_function(params["ch2"], ch2_pulse2)
sequence.add_segment(segment)

measure_time = params["pulse1"]["time"] + params["pulse2"]["time"]

sequence.setup_sequence([("pulse1", 1), ("pulse2", 1)])

###
m4i.setup_sequence(sequence)
sample_rate = 1e8
dg = Digitizer(False)
val = dg.configure_system(
    mode=2,
    sample_rate=sample_rate,
    segment_size=int(measure_time.to("s").magnitude * sample_rate),
)
val = dg.configure_trigger(
    source = 'external',
    edge = 'rising',
    level = 30,
)

###
dg.arm_digitizer()
time.sleep(0.1)
m4i.start_sequence()
m4i.wait_for_sequence_complete()
digitizer_data = dg.get_data()

ch1_data = digitizer_data[0][0]
ch2_data = digitizer_data[1][0]

plt.plot(ch1_data)
plt.plot(ch2_data)
plt.show()

m4i.stop_sequence()
#400ns delay on the second board