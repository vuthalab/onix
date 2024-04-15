import time

import numpy as np
from onix.units import ureg
from onix.experiments.shared import (
    m4i,
    dg,
    update_parameters_from_shared,
    setup_digitizer,
    save_data,
)
from tqdm import tqdm

from onix.sequences.antihole_fid import AntiholeFID
import matplotlib.pyplot as plt
from onix.analysis.power_spectrum import PowerSpectrum


## function to run the experiment
def get_sequence(params):
    sequence = AntiholeFID(params)
    return sequence

def run_sequence(sequence, params: dict, show_progress: bool = False, skip_setup = False):
    sequence.setup_sequence()
    if not skip_setup:
        m4i.setup_sequence(sequence)

    dg.start_capture()
    time.sleep(0.1)

    sequence_repeats_per_transfer = params["sequence_repeats_per_transfer"]
    data_transfer_repeats = params["data_transfer_repeats"]
    transmissions = []

    for kk in range(data_transfer_repeats):
        for ll in range(sequence_repeats_per_transfer):
            if show_progress:
                print(
                    f"{ll / sequence_repeats_per_transfer  * 100:.0f}%"
                )  # TODO: use tqdm progress bar, for kk too
            m4i.start_sequence()
            m4i.wait_for_sequence_complete()
        m4i.stop_sequence()

        timeout = 1
        dg.wait_for_data_ready(timeout)
        sample_rate, digitizer_data = dg.get_data()

        transmissions.append(np.array(digitizer_data[0]))

    return transmissions


## parameters
default_params = {
    "name": "Antihole FID",
    "sequence_repeats_per_transfer": 1,
    "data_transfer_repeats": 1,
    "ao": {
        "center_frequency": 78 * ureg.MHz,
    },
    "eos": {
        "ac": {
            "name": "eo_ac",
            "amplitude": 4500,  # 4500
            "offset": -300.0 * ureg.MHz,
        },
        "bb": {
            "name": "eo_bb",
            "amplitude": 1900,  # 1900
            "offset": -300 * ureg.MHz,
        },
        "ca": {
            "name": "eo_ca",
            "amplitude": 1400,  # 1400
            "offset": -300 * ureg.MHz,
        },
    },
    "chasm": {
        "transitions": ["bb", "bb"], #, "rf_both"
        "scan": 5 * ureg.MHz,
        "durations": 10 * ureg.ms,
        "repeats": 50,
        "detunings": [0 * ureg.MHz, 13 * ureg.MHz],
        "ao_amplitude": 2000,
    },
    "antihole": {
        "transitions": ["ac", "ca"], #, "rf_b" (for rf assist)
        "durations": 10 * ureg.ms,
        "repeats": 50,
        "detunings": 0 * ureg.MHz,
        "ao_amplitude": 2000,
    },
    "fid_detect": {
        "transition": "bb",
        "trigger_channel": 2,
        "randomize": False,
        "probe_detuning": 13 * ureg.MHz,
        "ao_pump_amplitude": 2000,
        "ao_probe_amplitude": 450,
        "pump_time": 20 * ureg.us,
        "probe_time": 20 * ureg.us,
        "delay_time": 2 * ureg.us,
        "probe_phase": 0,
        "cycles": {
            "chasm": 0,
            "antihole": 10000,
            "rf": 0,
        },
        "delay": 8 * ureg.us,
    },
    "digitizer": {
        "sample_rate": 100e6,
        "ch1_range": 2,
        "ch2_range": 2,
    },
    "field_plate": {
        "amplitude": 4000,
        "use": True,
        "stark_shift": 2 * ureg.MHz,
    }
}
default_params = update_parameters_from_shared(default_params)

default_sequence = get_sequence(default_params)
default_sequence.setup_sequence()
setup_digitizer(
    default_sequence.analysis_parameters["digitizer_duration"],
    default_sequence.num_of_record_cycles(),
    default_params["sequence_repeats_per_transfer"],
    ch1_range=default_params["digitizer"]["ch1_range"],
    ch2_range=default_params["digitizer"]["ch2_range"],
    sample_rate=default_params["digitizer"]["sample_rate"],
)

## test
params = default_params.copy()
sequence = get_sequence(params)
data = run_sequence(sequence, params)
#data_id = save_data(sequence, params, *data)
#print(data_id)

times = np.arange(len(data[0][0])) / params["digitizer"]["sample_rate"] * 1e6
plt.plot(times, np.average(data[0], axis=0)); plt.show();
plt.plot(times, data[0][:10].T); plt.xlabel("Time (us)"); plt.ylabel("Photodiode voltage (V)"); plt.show();

## spectrum
pss = []
for d in data[0]:
    ps = PowerSpectrum(len(times), 1 / params["digitizer"]["sample_rate"])
    ps.add_data(d)
    pss.append((ps.f, ps.voltage_spectrum, ps.error_signal_average))
ps_avg = PowerSpectrum(len(times), 1 / params["digitizer"]["sample_rate"])
ps_avg.add_data(np.average(data[0], axis=0))
plt.plot(ps_avg.f, ps_avg.voltage_spectrum, label="fridge off")
#plt.plot(*a, label="fridge on")
#plt.plot(ps.f, ps.voltage_spectrum)
plt.xscale("log")
plt.yscale("log")
plt.xlabel("FFT frequency (Hz)")
plt.ylabel("Voltage noise density (V / $\\sqrt{\\mathrm{Hz}}$)")
plt.legend()
plt.show()

## empty
plt.plot([ps[1][np.abs(ps[0] - 11005502.75137569) == min(np.abs(ps[0] - 11005502.75137569))] for ps in pss])
plt.plot([ps[2] for ps in pss])
#plt.xscale("log")
plt.yscale("log")
plt.xlabel("Repeat index")
plt.ylabel("Height of the 11 MHz peak (V / $\\sqrt{\\mathrm{Hz}}$)")
plt.show()
