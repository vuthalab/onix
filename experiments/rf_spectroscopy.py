import time

import numpy as np
from onix.data_tools import save_experiment_data
from onix.headers.awg.M4i6622 import M4i6622
from onix.headers.pcie_digitizer.pcie_digitizer import Digitizer
from onix.sequences.rf_spectroscopy import RFSpectroscopy
from onix.experiments.helpers import data_averaging
from onix.units import ureg

try:
    m4i
    print("m4i is already defined.")
except Exception:
    m4i = M4i6622()

try:
    dg
    print("dg is already defined.")
except Exception:
    dg = Digitizer(False)

## parameters
default_params = {
    "wm_channel": 5,
    "repeats": 2,
    "ao": {
        "name": "ao_dp",
        "order": 2,
        "frequency": 74 * ureg.MHz,  # TODO: rename it to "center_frequency"
        "amplitude": 2000,
        "detect_amplitude": 650,
        "rise_delay": 1.1 * ureg.us,
        "fall_delay": 0.6 * ureg.us,
    },
    "eos": {
        "ac": {
            "name": "eo_ac",
            "amplitude": 4500,  #4500
            "offset": -300 * ureg.MHz,
        },
        "bb": {
            "name": "eo_bb",
            "amplitude": 2000,  #2000
            "offset": -300 * ureg.MHz,
        },
        "ca": {
            "name": "eo_ca",
            "amplitude": 1400,  #1400
            "offset": -300 * ureg.MHz,
        },
    },
    "field_plate": {
        "name": "field_plate",
        "use": False,
        "amplitude": 0,
        "stark_shift": 1 * ureg.MHz,
        "padding_time": 1 * ureg.ms,
    },
    "chasm": {
        "transition": "bb",
        "scan": 2 * ureg.MHz,
        "scan_rate": 0.5 * ureg.MHz / ureg.s,
        "detuning": 0 * ureg.MHz,
    },
    "antihole": {
        "transitions": ["ac", "ca"],
        "scan": 0 * ureg.MHz,
        "scan_rate": 0 * ureg.MHz / ureg.s,
        "detuning": 0 * ureg.MHz,
        "duration_no_scan": 0.1 * ureg.s
    },
    "detect": {
        "transition": "bb",
        "trigger_channel": 2,
        "detunings": np.linspace(-1., 1, 40) * ureg.MHz,
        "randomize": True,
        "on_time": 10 * ureg.us,
        "off_time": 2 * ureg.us,
        "chasm_repeats": 1,  # change the names of detection repeats
        "antihole_repeats": 1,
        "rf_repeats": 1,
    },
    "rf": {
        "name": "rf_coil",
        "transition": "ab",
        "amplitude": 4200,
        "offset": 100 * ureg.kHz,
        "detuning": 0 * ureg.kHz,
        "duration": 0.1 * ureg.ms,
    },
}
default_sequence = RFSpectroscopy(
    ao_parameters=default_params["ao"],
    eos_parameters=default_params["eos"],
    field_plate_parameters=default_params["field_plate"],
    chasm_parameters=default_params["chasm"],
    antihole_parameters=default_params["antihole"],
    rf_parameters=default_params["rf"],
    detect_parameters=default_params["detect"],
)
default_sequence.setup_sequence()

digitizer_time_s = default_sequence.analysis_parameters["digitizer_duration"].to("s").magnitude
sample_rate = 1e8
dg.configure_system(
    mode=2,
    sample_rate=sample_rate,
    segment_size=int(digitizer_time_s * sample_rate),
    segment_count=default_sequence.num_of_records() * default_params["repeats"],
    voltage_range=2,
)
dg.configure_trigger(
    source="external",
)


## function to run the experiment
def run_experiment(params):
    sequence = RFSpectroscopy(  # Only change the part that changed
        ao_parameters=params["ao"],
        eos_parameters=params["eos"],
        field_plate_parameters=params["field_plate"],
        chasm_parameters=params["chasm"],
        antihole_parameters=params["antihole"],
        rf_parameters=params["rf"],
        detect_parameters=params["detect"],
    )
    sequence.setup_sequence()

    digitizer_time_s = sequence.analysis_parameters["digitizer_duration"].to("s").magnitude
    dg.initialize()
    sample_rate = 1e8
    dg.configure_system(
        mode=2,
        sample_rate=sample_rate,
        segment_size=int(digitizer_time_s * sample_rate),
        segment_count=sequence.num_of_records() * params["repeats"],
        voltage_range=2,
    )
    dg.configure_trigger(
        source="external",
    )

    m4i.setup_sequence(sequence)

    transmissions = None
    dg.arm_digitizer()
    time.sleep(0.1)

    for kk in range(params["repeats"]):
        print(f"{kk / params['repeats'] * 100:.0f}%")
        m4i.start_sequence()
        m4i.wait_for_sequence_complete()
    m4i.stop_sequence()

    digitizer_data = dg.get_data()
    transmissions = np.array(digitizer_data[0])
    monitors = np.array(digitizer_data[1])

    photodiode_times = [kk / sample_rate for kk in range(len(transmissions[0]))]
    transmissions_avg, transmissions_err = data_averaging(transmissions, sample_rate, sequence.analysis_parameters["detect_pulse_times"])
    monitors_avg, monitors_err = data_averaging(monitors, sample_rate, sequence.analysis_parameters["detect_pulse_times"])

    data = {
        "transmissions_avg": transmissions_avg,
        "transmissions_err": transmissions_err,
        "monitors_avg": monitors_avg,
        "monitors_err": monitors_err,
    }
    headers = {
        "params": params,
        "detunings": sequence.analysis_parameters["detect_detunings"]
    }
    name = "RF Spectroscopy"
    data_id = save_experiment_data(name, data, headers)
    print(data_id)
    dg.close()

## scan
rf_frequencies = np.linspace(80, 200, 30) * ureg.kHz
#rf_frequencies = np.array([100]) * ureg.kHz
antihole_center_frequencies = np.linspace(70, 85, 30) * ureg.MHz
params = default_params.copy()
for kk in range(len(rf_frequencies)):
    params["rf"]["offset"] = rf_frequencies[kk]
    params["ao"]["frequency"] = antihole_center_frequencies[kk]
    run_experiment(params)

## empty