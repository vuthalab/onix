import time

import numpy as np
import matplotlib.pyplot as plt

from onix.data_tools import save_experiment_data
from onix.sequences.sequence import AWGSinePulse, AWGSineTrain, Segment, Sequence, TTLPulses
from onix.units import ureg, Q_
from onix.sequences.pd_noise import pdNoiseMeasurement

from onix.headers.pcie_digitizer.pcie_digitizer import Digitizer
from onix.headers.awg.M4i6622 import M4i6622

from tqdm import tqdm

m4i = M4i6622()

##

T = 100 * ureg.ms
sample_rate = int(1e8)
segment_size = int(T.to("s").magnitude * sample_rate)
segment_count = 500
dg = Digitizer(False)
val = dg.configure_system(
    mode = 1,
    sample_rate = sample_rate,
    segment_size = segment_size,
    segment_count = segment_count,
    voltage_range = 2000
)
val = dg.configure_trigger(source = "software")
# acq_params = dg.get_acquisition_parameters()


test = None
dg.arm_digitizer()
time.sleep(0.1)

digitizer_data = dg.get_data()
f = np.fft.rfftfreq(len(digitizer_data[0][0]), 1/sample_rate)

fts = []
ft2s = np.zeros((segment_count, int(len(digitizer_data[0][0])/2 + 1)))

for i, data in enumerate(digitizer_data[0]):
    ft = np.fft.rfft(data)
    fts.append(ft)
    # plt.plot(f, np.abs(ft))
    ft2 = np.square(np.abs(ft))
    ft2s[i, :] = ft2

ft2s_avg = np.sqrt(np.average(ft2s, axis=0)/segment_count)
print(ft2s)

# test = digitizer_data[0][0]
# ft = np.fft.rfft(test)
# plt.plot(f, np.abs(ft))
plt.ylabel(r"$\mathrm{V}/\sqrt{\mathrm{Hz}}$")
plt.xlabel("Frequency (Hz)")
plt.loglog(f, ft2s_avg)
plt.show()


##

def get_vspectrum(V, sample_rate):
    t = np.arange(0,len(V))
    t = t/sample_rate

    V = V - np.average(V)

    T = t[-1] - t[0]
    dt = t[1] - t[0]
    sample_time = 1/dt

    V_T = V/np.sqrt(T)
    V_f = np.fft.fft(V_T)*dt
    S_V = np.abs(V_f)**2
    f = np.fft.fftfreq(len(V_T),dt)

    W_V = 2*S_V[f>0]
    f = f[f>0]
    df = f[1]-f[0]

    return W_V, f

##

baselineW_V = np.loadtxt("/home/onix/Documents/code/onix/experiments/baseline.txt")

##

params = {
    "digitizer_channel": 0,

    "ao": {
        "channel": 0,
        "frequency": 80e6, # Hz
        "amplitude": 300
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

## Digitizer setup

T = params["detect"]["sample_time"]
sample_rate = int(1e8)
segment_size = int(T * sample_rate)
segment_count = 10
dg = Digitizer(False)
val = dg.configure_system(
    mode = 1,
    sample_rate = sample_rate,
    segment_size = segment_size,
    segment_count = segment_count,
    voltage_range = 2000
)

val = dg.configure_trigger(
    edge = 'rising',
    level = 30,
    source =-1,
    coupling = 1,
    range = 10000
)

##

m4i.setup_sequence(sequence)

for kk in range(0):
    m4i.start_sequence()
    m4i.wait_for_sequence_complete()

dg.arm_digitizer()


print("taking data")
for i in tqdm(range(segment_count)):
    m4i.start_sequence()
    m4i.wait_for_sequence_complete()

m4i.stop_sequence()

Vs = dg.get_data()[0]

##

Vavg = np.mean(Vs, axis=0)

#plt.plot(np.arange(0,len(Vavg))/1e8, Vs[0])
plt.plot(np.arange(0,len(Vavg))/1e8, Vavg)

plt.xlabel("Time (s)")
plt.ylabel("Transmissions voltage (V)")
plt.show()

# W_Vs = []
# f = None
# print("Computing voltage spectra")
# for i in tqdm(range(len(Vs))):
#     W_V, f_ = get_vspectrum(Vs[i],sample_rate)
#     f = f_
#     W_Vs.append(W_V)

##

W_V_avg = np.abs(np.average(W_Vs, axis=0) - baselineW_V)


plt.ylabel(r"Avg voltage spectrum - baseline $\mathrm{V}/\sqrt{\mathrm{Hz}}$")
plt.xlabel("Frequency (Hz)")
plt.loglog(f, np.sqrt(np.abs(W_V_avg)))
plt.loglog(f, np.sqrt(baselineW_V), label="baseline")

plt.legend()
plt.show()



## longer test for pulse tube

def trigger():
    m4i.set_ttl_output(0, True)
    time.sleep(0.01)
    m4i.set_ttl_output(0, False)


T = 2000 * 1e-3
sample_rate = int(1e8)
segment_size = int(T * sample_rate)
segment_count = 5
dg = Digitizer(False)
val = dg.configure_system(
    mode = 1,
    sample_rate = sample_rate,
    segment_size = segment_size,
    segment_count = segment_count,
    voltage_range = 2000
)

val = dg.configure_trigger(
    edge = 'rising',
    level = 30,
    source =-1,
    coupling = 1,
    range = 10000
)

m4i.start_sine_outputs()

dg.arm_digitizer()

m4i.set_sine_output(0, 80e6, 350)

for i in tqdm(range(segment_count)):
    trigger()
    time.sleep(T + 10e-3)

m4i.stop_sine_outputs()

Vs = dg.get_data()[0]

W_Vs = []
f = None
print("Computing voltage spectra")
for i in tqdm(range(len(Vs))):
    W_V, f_ = get_vspectrum(Vs[i],sample_rate)
    f = f_
    W_Vs.append(W_V)













