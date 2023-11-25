import time

import numpy as np
import matplotlib.pyplot as plt

from onix.data_tools import save_experiment_data
from onix.sequences.sequence import AWGSinePulse, AWGSineTrain, Segment, Sequence, TTLPulses
from onix.units import ureg, Q_
from onix.sequences.pd_noise import pdNoiseMeasurement
from onix.analysis.debug.laser_linewidth import LaserLinewidth

from onix.headers.pcie_digitizer.pcie_digitizer import Digitizer
from onix.headers.digitizer import DigitizerVisa
from onix.headers.awg.M4i6622 import M4i6622

from tqdm import tqdm

m4i = M4i6622()

##

params = {
    "digitizer_channel": 0,

    "ao": {
        "channel": 0,
        "frequency": 80e6, # Hz
        "amplitude": 2200
    },

    "detect": {
        "sample_time" : 100e-3, # s
        "buffer": 10e-3 # s
    }

}

## Sequence Setup
sequence = pdNoiseMeasurement(
    ao_parameters=params["ao"],
    detect_parameters=params["detect"],
    digitizer_channel=params["digitizer_channel"]
)
sequence.setup_sequence()
m4i.setup_sequence(sequence)

## Digitizer setup PCIE

T = params["detect"]["sample_time"]
sample_rate = int(1e8)
segment_size = int(T * sample_rate)
segment_count = 10
repeats = 10
dg = Digitizer(False)
val = dg.configure_system(
    mode = 1,
    sample_rate = sample_rate,
    segment_size = segment_size,
    segment_count = segment_count,
    voltage_range = 2,
)

val = dg.configure_trigger(
    source = "external",
)

## Digitizer setup Agilent
# sample_rate = 1e7
# segment_count = 100
# segment_size = int(T * sample_rate)
# T = params["detect"]["sample_time"]
# dg.configure_acquisition(
#     sample_rate=sample_rate,
#     samples_per_record=segment_size,
#     num_records=segment_count,
# )
# dg.configure_channels(channels=[1, 2], voltage_range=2)
# dg.set_trigger_source_external()
# dg.set_arm(triggers_per_arm=segment_count)


##
Vt = np.zeros((0, segment_size))

for kk in range(repeats):
    dg.arm_digitizer()
    #dg.initiate_data_acquisition()

    for i in tqdm(range(segment_count)):
        m4i.start_sequence()
        m4i.wait_for_sequence_complete()

    #Vt, Vm = dg.get_waveforms([1,2], records=(1,segment_count))
    Vt = np.append(Vt, dg.get_data()[0], axis=0)

m4i.stop_sequence()
Vtavg = np.mean(Vt, axis=0)
print(Vtavg)

##
spectrum = LaserLinewidth(
    error_signals = Vt,
    time_resolution = 1 / sample_rate,
    discriminator_slope = 1,  # not used
    max_points_per_decade = 100,
)


##
plt.plot(np.arange(0,len(Vtavg))/sample_rate, Vtavg, label="Transmission Avg")

plt.xlabel("Time (s)")
plt.ylabel("PD voltage (V)")
plt.legend(frameon=True)
plt.show()

##
#plt.ylabel(r"Avg voltage spectrum - baseline $\mathrm{V}/\sqrt{\mathrm{Hz}}$")
plt.ylabel(r"Avg voltage spectrum $\mathrm{V}/\sqrt{\mathrm{Hz}}$")
plt.xlabel("Frequency (Hz)")
plt.loglog(spectrum.f, np.sqrt(spectrum.W_V))

#plt.legend()
plt.show()



## Save Data

data = {
    "f": spectrum.f,
    "W_V": spectrum.W_V,
    "Vtavg": Vtavg,
}
headers = {
    "params": params,
}
name = "PD Noise Spectra"
data_id = save_experiment_data(name, data, headers)
print(data_id)
del spectrum
del Vt
del Vtavg

##