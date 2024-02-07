import numpy as np
import matplotlib.pyplot as plt
from tqdm import tqdm
import time

from onix.data_tools import save_experiment_data
from onix.units import ureg, Q_
from onix.sequences.pd_noise import pdNoiseMeasurement
from onix.analysis.correlate import get_correlated_signal
from onix.analysis.debug.laser_linewidth import LaserLinewidth
from onix.analysis.power_spectrum import PowerSpectrum, CCedPowerSpectrum

from onix.headers.pcie_digitizer.pcie_digitizer import Digitizer
from onix.headers.digitizer import DigitizerVisa
from onix.headers.awg.M4i6622 import M4i6622
from onix.headers.quarto_intensity_control import Quarto


try:
    m4i
    print("m4i is already defined.")
except Exception:
    m4i = M4i6622()

##
try:
    q
except Exception:
    q = Quarto("/dev/ttyACM2")

params = {
    "digitizer_channel": 2,
    "pid_trigger_channel": 1,

    "ao": {
        "channel": 1,
        "frequency": 75e6, # Hz
        "amplitude": 800
    },

    "detect": {
        "sample_time" : 50e-3, # s
        "buffer": 20e-3 # s
    },

    "device": "quarto",  # "quarto", "gage"
    "use_sequence": True,
    "chasm_burning": False,
    "repeats": 5,
}

## Sequence Setup
if params["chasm_burning"]:
    print("chasm burning started")
    m4i.start_sine_outputs()
    for f in np.linspace(params["ao"]["frequency"] - 2e6, params["ao"]["frequency"] + 2e6, 40):
        m4i.set_sine_output(params["ao"]["channel"], f, 2000)
        time.sleep(0.1)
    m4i.set_sine_output(params["ao"]["channel"], params["ao"]["frequency"], 2000)
    time.sleep(1)
    m4i.stop_sine_outputs()
    print("chasm burning finished.")

if params["use_sequence"]:
    sequence = pdNoiseMeasurement(
        ao_parameters=params["ao"],
        detect_parameters=params["detect"],
        digitizer_channel=params["digitizer_channel"],
        pid_trigger_channel=params["pid_trigger_channel"],
    )
    sequence.setup_sequence()
    m4i.setup_sequence(sequence)

else:
    m4i.set_sine_output(params["ao"]["channel"], params["ao"]["frequency"], params["ao"]["amplitude"])
    m4i.set_ttl_output(params["pid_trigger_channel"], True)
    m4i.start_sine_outputs()

## Digitizer setup PCIE
if params["device"] == "gage":
    T = params["detect"]["sample_time"]
    sample_rate = 100e6
    segment_size = int(T * sample_rate)
    try:
        dg
    except Exception:
        dg = Digitizer()
    segment_count = 1
    dg.set_acquisition_config(
        num_channels=2,
        sample_rate=sample_rate,
        segment_size=segment_size,
        segment_count=segment_count,
    )
    dg.set_channel_config(channel=1, range=5, high_impedance=False)
    dg.set_channel_config(channel=2, range=5, high_impedance=False)
    if params["use_sequence"]:
        dg.set_trigger_source_edge()
    else:
        dg.set_trigger_source_software()
    dg.write_configs_to_device()


## Digitizer setup Quarto
if params["device"] == "quarto":
    try:
        q
    except Exception:
        q = Quarto("/dev/ttyACM1")
    sample_rate = 500e3
    T = 0.1
    params["detect"]["sample_time"] = T
    segment_size = int(T * sample_rate)


## collect data
print("data collection started.")
if params["device"] == "gage":
    Vt = np.zeros((0, segment_size))
    Vm = np.zeros((0, segment_size))
elif params["device"] == "quarto":
    Vt = np.zeros((0, segment_size))

for kk in range(params["repeats"]):
    if params["device"] == "gage":
        dg.start_capture()
        if params["use_sequence"]:
            m4i.start_sequence()
            m4i.wait_for_sequence_complete()
        else:
            time.sleep(T + 0.1)
        dg.wait_for_data_ready(1)
        digitizer_sample_rate, digitizer_data = dg.get_data()
        Vt = np.append(Vt, digitizer_data[0], axis=0)
        Vm = np.append(Vm, digitizer_data[1], axis=0)
    elif params["device"] == "quarto":
        time.sleep(T + 0.1)
        Vt = np.append(Vt, [q.get_error_data()], axis=0)

    print(f"{kk + 1} / {params['repeats']} finished")

if params["device"] == "gage" and params["use_sequence"]:
    m4i.stop_sequence()

print("data collection ended.")

##
if params["device"] == "gage":
    N_Vt = len(Vt)
    time_resolution = 1 / sample_rate
    spectrum0 = spectrum1 = PowerSpectrum(N_Vt, time_resolution)
    spectrum0.add_data(Vt)
    spectrum1.add_data(Vm)

    spectrum_cc = CCedPowerSpectrum(N_Vt, time_resolution)
    spectrum_cc.add_data(Vt, Vm)

    Vtavg = np.mean(Vt)
    Vmavg = np.mean(Vm)
    print(Vtavg, Vmavg)

elif params["device"] == "quarto":
    N_Vt = len(Vt)
    time_resolution = 1 / sample_rate
    spectrum0 = PowerSpectrum(N_Vt, time_resolution)
    Vtavg = np.mean(Vt)
    print(Vtavg)


## Plot Spectrum
plt.ylabel("Avg fractional noise spectrum $\\sqrt{\\mathrm{Hz}}^{-1}$")
plt.xlabel("Frequency (Hz)")

if params["device"] == "gage":
    plt.loglog(spectrum0.f, spectrum0.relative_voltage_spectrum / Vtavg, label="channel 1", alpha=0.6)
    plt.loglog(spectrum1.f, spectrum1.relative_voltage_spectrum / Vmavg, label="channel 2", alpha=0.6)
    plt.loglog(spectrum_cc.f, np.sqrt(np.abs(spectrum_cc.relative_voltage_spectrum)) / np.sqrt(Vtavg * Vmavg), label="cross correlation", alpha=0.6)

elif params["device"] == "quarto":
    plt.loglog(spectrum0.f, np.sqrt(spectrum0.W_V) / np.abs(Vtavg), label="channel 1", alpha=0.6)
plt.legend()
plt.show()


## Save Data
if params["device"] == "gage":
    data = {
        "f": spectrum0.f,
        "W_V1": spectrum0.W_V,
        "V1_avg": Vtavg,
        "W_V2": spectrum1.W_V,
        "V2_avg": Vmavg,
        "W_Vcc": np.abs(spectrum_cc.W_V),
        "Vcc_avg": np.sqrt(Vtavg * Vmavg),
    }
elif params["device"] == "quarto":
    data = {
        "f": spectrum0.f,
        "W_V1": spectrum0.W_V,
        "V1_avg": Vtavg,
    }

p_gain = q.get_p_gain()
i_time = q.get_i_time()
d_time = q.get_d_time()
pid_state = q.get_pid_state()
headers = {
    "params": params,
    "pid_state": q.pid_state,
    "p_gain": q.p_gain,
    "i_time": q.i_time,
    "d_time": q.d_time,
}
name = "PD Noise Spectra"
data_id = save_experiment_data(name, data, headers)
print(data_id)
if params["device"] == "gage":
    del Vt
    del Vm
    del Vtavg
    del Vmavg
    del spectrum0
    del spectrum1
    del spectrum_cc
elif params["device"] == "quarto":
    del Vt
    del Vtavg
    del spectrum0

##