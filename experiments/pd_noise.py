import time

import numpy as np
import matplotlib.pyplot as plt

from onix.data_tools import save_experiment_data
from onix.sequences.sequence import AWGSinePulse, AWGSineTrain, Segment, Sequence, TTLPulses
from onix.units import ureg, Q_
from onix.sequences.pd_noise import pdNoiseMeasurement

from onix.headers.pcie_digitizer.pcie_digitizer import Digitizer
from onix.headers.digitizer import DigitizerVisa
from onix.headers.awg.M4i6622 import M4i6622

from tqdm import tqdm

m4i = M4i6622()
#dg = DigitizerVisa("192.168.0.125")

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
        "amplitude": 1400
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

## Digitizer setup PCIE

T = params["detect"]["sample_time"]
sample_rate = int(1e7)
segment_size = int(T * sample_rate)
segment_count = 10
dg = Digitizer(False)
val = dg.configure_system(
    mode = 2,
    sample_rate = sample_rate,
    segment_size = segment_size,
    segment_count = segment_count,
    voltage_range = 2000
)

val = dg.configure_trigger(
    edge = 'rising',
    level = 30,
    source = "external",
    coupling = "DC",
    range = 10000
)

## Digitizer setup Agilent
sample_rate = 1e7
segment_count = 100
T = params["detect"]["sample_time"]
dg.configure_acquisition(
    sample_rate=sample_rate,
    samples_per_record=int(T * sample_rate),
    num_records=segment_count,
)
dg.configure_channels(channels=[1, 2], voltage_range=2)
dg.set_trigger_source_external()
dg.set_arm(triggers_per_arm=segment_count)


##

m4i.setup_sequence(sequence)
dg.arm_digitizer()

#dg.initiate_data_acquisition()

print("taking data")
for i in tqdm(range(segment_count)):
    m4i.start_sequence()
    m4i.wait_for_sequence_complete()

m4i.stop_sequence()

#Vt, Vm = dg.get_waveforms([1,2], records=(1,segment_count))

Vt, Vm = dg.get_data()

##

Vtavg = np.mean(Vt, axis=0)
Vmavg = np.mean(Vm, axis=0)

plt.plot(np.arange(0,len(Vtavg))/sample_rate, Vt[0], label="Transmission")
#plt.plot(np.arange(0,len(Vtavg))/sample_rate, Vm[0], label="Monitor")
plt.plot(np.arange(0,len(Vtavg))/sample_rate, Vtavg, label="Transmission Avg")

plt.xlabel("Time (s)")
plt.ylabel("PD voltage (V)")
plt.legend(frameon=True)
plt.show()

##

W_Vs = []
f = None
print("Computing voltage spectra")
for i in tqdm(range(len(Vt))):
    W_V, f_ = get_vspectrum(Vt[i],sample_rate)
    f = f_
    W_Vs.append(W_V)

##

W_V_avg = np.average(W_Vs, axis=0) #- baselineW_V)


#plt.ylabel(r"Avg voltage spectrum - baseline $\mathrm{V}/\sqrt{\mathrm{Hz}}$")
plt.ylabel(r"Avg voltage spectrum $\mathrm{V}/\sqrt{\mathrm{Hz}}$")
plt.xlabel("Frequency (Hz)")
plt.loglog(f, np.sqrt(W_V_avg))
#plt.loglog(f, np.sqrt(baselineW_V), label="baseline")

plt.legend()
plt.show()



## Save Data

data = {
    "f": f,
    "W_V_avg": W_V_avg,
    "Vtavg": Vtavg,
    "Vmavg": Vmavg
}
headers = {
    "params": params,
}
name = "PD Noise Spectra"
data_id = save_experiment_data(name, data, headers)
print(data_id)













