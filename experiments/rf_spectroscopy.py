import time

import numpy as np
from onix.data_tools import save_experiment_data
from onix.headers.awg.M4i6622 import M4i6622
from onix.headers.pcie_digitizer.pcie_digitizer import Digitizer
from onix.sequences.rf_spectroscopy import RFSpectroscopy
from onix.units import ureg

m4i = M4i6622()

## parameters
params = {
    "wm_channel": 5,
    "repeats": 2,
    "ao": {
        "channel": 0,
        "order": 2,
        "frequency": 80 * ureg.MHz,
        "amplitude": 0,
        "detect_amplitude": 0,
        "rise_delay": 2 * ureg.us,
        "fall_delay": 1 * ureg.us,
    },
    "eos": {
        "ac": {
            "channel": 4,
            "amplitude": 0,
            "offset": -300 * ureg.MHz,
        },
        "bb": {
            "channel": 1,
            "amplitude": 0,
            "offset": -300 * ureg.MHz,
        },
        "ca": {
            "channel": 5,
            "amplitude": 0,
            "offset": -300 * ureg.MHz,
        },
    },
    "field_plate": {
        "channel": 6,
        "use": True,
        "amplitude": 0,
        "stark_shift": 1 * ureg.MHz,
        "padding_time": 1 * ureg.ms,
    },
    "chasm": {
        "transition": "bb",
        "scan": 1.5 * ureg.MHz,
        "scan_rate": 1 * ureg.MHz / ureg.s,
        "detuning": 0 * ureg.MHz,
    },
    "antihole": {
        "transitions": ["ac", "ca"],
        "scan": 0.1 * ureg.MHz,
        "scan_rate": 1 * ureg.MHz / ureg.s,
        "detuning": 0 * ureg.MHz,
    },
    "detect": {
        "transition": "bb",
        "trigger_channel": 2,
        "detunings": np.linspace(-1, 1, 8) * ureg.MHz,
        "randomize": True,
        "on_time": 10 * ureg.us,
        "off_time": 2 * ureg.us,
        "chasm_repeats": 10,
        "antihole_repeats": 10,
        "rf_repeats": 100,
    },
    "rf": {
        "channel": 2,
        "transition": "ab",
        "amplitude": 0,
        "offset": 0 * ureg.kHz,
        "detuning": 0 * ureg.kHz,
        "duration": 1 * ureg.ms,
    },
}

## setup sequence
sequence = RFSpectroscopy(
    ao_parameters=params["ao"],
    eos_parameters=params["eos"],
    field_plate_parameters=params["field_plate"],
    chasm_parameters=params["chasm"],
    antihole_parameters=params["antihole"],
    rf_parameters=params["rf"],
    detect_parameters=params["detect"],
)
sequence.setup_sequence()

## setup the awg
m4i.setup_sequence(sequence)
digitizer_time_s = sequence.analysis_parameters["digitizer_duration"].to("s").magnitude

## setup digitizer
sample_rate = 1e8
dg = Digitizer(False)
dg.configure_system(
    mode=1,
    sample_rate=sample_rate,
    segment_size=int(digitizer_time_s * sample_rate),
    segment_count=sequence.num_of_records() * params["repeats"],
    voltage_range=2,
)
dg.configure_trigger(
    source="external",
)

## Data cleaning

def data_cleaning(data):
    pulse_times = sequence.analysis_parameters["detect_pulse_times"]
    data_avg = []
    data_err = []

    for run in data:

        scans_avg = []
        scans_err = []

        for pulse in pulse_times:
            start = int(pulse[0] * sample_rate)
            end = int(pulse[1] * sample_rate)

            scans_avg.append(np.mean(run[start: end]))
            scans_err.append(np.std(run[start:end])/ np.sqrt(len(run[start:end])))

        data_avg.append(scans_avg)
        data_err.append(scans_err)

    return data_avg, data_err


## take data
epoch_times = []
transmissions = None
dg.arm_digitizer()
time.sleep(0.1)

for kk in range(params["repeats"]):
    print(f"{kk / params['repeats'] * 100:.0f}%")
    m4i.start_sequence()
    epoch_times.append(time.time())
    m4i.wait_for_sequence_complete()
m4i.stop_sequence()

digitizer_data = dg.get_data()
transmissions = np.array(digitizer_data[0])

photodiode_times = [kk / sample_rate for kk in range(len(transmissions[0]))]

transmissions_avg, transmissions_err = data_cleaning(transmissions)


## save data
data = {
    "times": photodiode_times,
    "transmissions_avg": transmissions_avg,
    "transmissions_err": transmissions_err
    "epoch_times": epoch_times,
    "detunings:" sequence.analysis_parameters["detect_detunings"]
}
headers = {
    "params": params,
}
name = "RF Spectroscopy"
data_id = save_experiment_data(name, data, headers)
print(data_id)

## empty
