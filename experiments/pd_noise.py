import numpy as np
import matplotlib.pyplot as plt
from tqdm import tqdm

from onix.data_tools import save_experiment_data
from onix.units import ureg, Q_
from onix.sequences.pd_noise import pdNoiseMeasurement
from onix.analysis.correlate import get_correlated_signal
from onix.analysis.debug.laser_linewidth import LaserLinewidth

from onix.headers.pcie_digitizer.pcie_digitizer import Digitizer
from onix.headers.digitizer import DigitizerVisa
#from onix.headers.awg.M4i6622 import M4i6622


#m4i = M4i6622()

##

params = {
    "digitizer_channel": 0,
    "channels": 1,

    "ao": {
        "channel": 0,
        "frequency": 80e6, # Hz
        "amplitude": 0
    },

    "detect": {
        "sample_time" : 1000e-3, # s
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
segment_count = 2
repeats = 10
dg = Digitizer(False)
val = dg.configure_system(
    mode = params["channels"],
    sample_rate = sample_rate,
    segment_size = segment_size,
    segment_count = segment_count,
    voltage_range = 2,
)

val = dg.configure_trigger(
    source = "software",
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
Vm = np.zeros((0, segment_size))

for kk in range(repeats):
    dg.arm_digitizer()
    #dg.initiate_data_acquisition()

    #for i in tqdm(range(segment_count)):
    #    m4i.start_sequence()
    #    m4i.wait_for_sequence_complete()

    #Vt, Vm = dg.get_waveforms([1,2], records=(1,segment_count))
    Vt = np.append(Vt, dg.get_data()[0], axis=0)
    if params["channels"] == 2:
        Vm = np.append(Vm, dg.get_data()[1], axis=0)

m4i.stop_sequence()
Vtavg = np.mean(Vt)
print(Vtavg)
if params["channels"] == 2:
    Vmavg = np.mean(Vm)
    print(Vtavg, Vmavg)

##
spectrum0 = LaserLinewidth(
    error_signals = Vt,
    time_resolution = 1 / sample_rate,
    discriminator_slope = 1,  # not used
    max_points_per_decade = 100,
)
if params["channels"] == 2:
    spectrum1 = LaserLinewidth(
        error_signals = Vm,
        time_resolution = 1 / sample_rate,
        discriminator_slope = 1,  # not used
        max_points_per_decade = 100,
    )
    correlated = [get_correlated_signal(Vt[kk], Vm[kk]) for kk in range(len(Vt))]
    spectrum_correlation = LaserLinewidth(
        error_signals = correlated,
        time_resolution = 1 / sample_rate,
        discriminator_slope = 1,  # not used
        max_points_per_decade = 100,
    )
    spectrum_correlation1 = LaserLinewidth(
        error_signals = Vt,
        time_resolution = 1 / sample_rate,
        discriminator_slope = 1,  # not used
        max_points_per_decade = 100,
        correlation_error_signals = Vm,
    )

##
def get_correlated_signal(V1: np.ndarray, V2: np.ndarray) -> np.ndarray:
    V1_f = np.fft.fft(V1)
    V2_f = np.fft.fft(V2)
    return np.abs(np.fft.ifft(np.sqrt(np.conjugate(V1_f) * V2_f)))

## Plot Spectrum
#plt.ylabel(r"Avg voltage spectrum - baseline $\mathrm{V}/\sqrt{\mathrm{Hz}}$")
plt.ylabel("Avg voltage spectrum $\\mathrm{V}/\\sqrt{\\mathrm{Hz}}$")
plt.xlabel("Frequency (Hz)")
plt.loglog(spectrum0.f, np.sqrt(spectrum0.W_V), label="channel 1", alpha=0.6)
if params["channels"] == 2:
    plt.loglog(spectrum1.f, np.sqrt(spectrum1.W_V), label="channel 2", alpha=0.6)
    plt.loglog(spectrum_correlation.f, np.sqrt(np.abs(spectrum_correlation.W_V)), label="correlation", alpha=0.6)
    plt.loglog(spectrum_correlation1.f, np.sqrt(np.abs(spectrum_correlation1.W_V)), label="correlation_no_magnitude", alpha=0.6)
    plt.legend()
#plt.legend()
plt.show()


## Save Data

data = {
    "f": spectrum0.f,
    "W_V1": spectrum0.W_V,
    "V1_avg": Vtavg,
}
if params["channels"] == 2:
    data["V2_avg"] = Vmavg
    data["W_V2"] = spectrum1.W_V
    data["W_V_correlation"] = spectrum_correlation.W_V
    data["W_V_correlation_no_magnitude"] = spectrum_correlation1.W_V

headers = {
    "params": params,
}
name = "PD Noise Spectra"
data_id = save_experiment_data(name, data, headers)
print(data_id)
del spectrum0
del Vt
del Vtavg
if params["channels"] == 2:
    del correlated
    del spectrum1
    del spectrum_correlation
    del Vm
    del Vmavg

##