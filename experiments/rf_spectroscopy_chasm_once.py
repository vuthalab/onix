import time

import numpy as np
from onix.data_tools import save_experiment_data
from onix.headers.awg.M4i6622 import M4i6622
from onix.headers.pcie_digitizer.pcie_digitizer import Digitizer
from onix.sequences.rf_no_chasm import RFNoChasm
from onix.sequences.rf_chasm import RFChasm
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
    dg = Digitizer()


def burn_chasm(params):
    sequence = RFChasm(
        ao_parameters=params["ao"],
        eos_parameters=params["eos"],
        field_plate_parameters=params["field_plate"],
        chasm_parameters=params["chasm"],
    )
    sequence.setup_sequence()
    m4i.setup_sequence(sequence)
    m4i.start_sequence()
    m4i.wait_for_sequence_complete()
    m4i.stop_sequence()
    print("burned chasm")

## function to run the experiment
def run_experiment(params):
    t0 = time.time()
    sequence = RFNoChasm(  # Only change the part that changed
        ao_parameters=params["ao"],
        eos_parameters=params["eos"],
        field_plate_parameters=params["field_plate"],
        chasm_parameters=params["chasm"],
        antihole_parameters=params["antihole"],
        rf_parameters=params["rf"],
        detect_parameters=params["detect"],
    )
    sequence.setup_sequence()
    m4i.setup_sequence(sequence)
    t1 = time.time()
    print("setup sequence")

    transmissions = None
    dg.start_capture()
    time.sleep(0.1)

    for kk in range(params["repeats"]):
        print(f"{kk / params['repeats'] * 100:.0f}%")
        m4i.start_sequence()
        m4i.wait_for_sequence_complete()
    m4i.stop_sequence()
    print("stop sequence")

    dg.wait_for_data_ready(1)
    t2 = time.time()
    digitizer_sample_rate, digitizer_data = dg.get_data()
    transmissions = np.array(digitizer_data[0])
    monitors = np.array(digitizer_data[1])

    photodiode_times = [kk / digitizer_sample_rate for kk in range(len(transmissions[0]))]
    transmissions_avg, transmissions_err = data_averaging(transmissions, digitizer_sample_rate, sequence.analysis_parameters["detect_pulse_times"])
    monitors_avg, monitors_err = data_averaging(monitors, digitizer_sample_rate, sequence.analysis_parameters["detect_pulse_times"])

    #import matplotlib.pyplot as plt
    #plt.plot(photodiode_times, transmissions[0])
    #plt.show()

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
    t3 = time.time()

    print(data_id)
    print()

    # print(f"t1-t0 = {t1-t0}")
    # print(f"t2-t1 = {t2-t1}")
    # print(f"t3-t2 = {t3-t2}")


## parameters
default_params = {
    "wm_channel": 5,
    "repeats": 1,
    "ao": {
        "name": "ao_dp",
        "order": 2,
        "frequency": 74 * ureg.MHz,  # TODO: rename it to "center_frequency"
        "amplitude": 2000,
        "detect_amplitude": 450,
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
            "amplitude": 1900,  #1900
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
        "amplitude": 4500,
        "stark_shift": 2 * ureg.MHz,
        "padding_time": 5 * ureg.ms,
    },
    "chasm": {
        "transition": "bb",
        "scan": 3 * ureg.MHz,
        "scan_rate": 3000 * ureg.MHz / ureg.s,
        "detuning": 0 * ureg.MHz,
    },
    "antihole": {
        "transitions": ["ac", "ca"],
        "scan": 0 * ureg.MHz,
        "scan_rate": 0 * ureg.MHz / ureg.s,
        "detuning": 0 * ureg.MHz,
        "duration_no_scan": 0.2 * ureg.s,
        "rf_assist": {
            "use": False,
            "use_sequential": False,
            "name": "rf_coil",
            "transition": "ab",
            "offset_start": -110 * ureg.kHz, #-110, 30
            "offset_end": 20 * ureg.kHz, #20, 170
            "amplitude": 4200,
            "duration": 5 * ureg.ms,
        }
    },
    "detect": {
        "transition": "bb",
        "trigger_channel": 2,
        "detunings": np.linspace(-2, 2, 20) * ureg.MHz,
        "randomize": True,
        "on_time": 10 * ureg.us,
        "off_time": 2 * ureg.us,
        "chasm_repeats": 0,  # change the names of detection repeats
        "antihole_repeats": 100,
        "rf_repeats": 100,
    },
    "rf": {
        "name": "rf_coil",
        "transition": "ab",
        "amplitude": 1500,  # 4200
        "offset": -45 * ureg.kHz,
        "detuning": 0 * ureg.kHz,
        "duration": 0.5 * ureg.ms,
    },
}
default_sequence = RFNoChasm(
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
sample_rate = 25e6
dg.set_acquisition_config(
    num_channels=2,
    sample_rate=sample_rate,
    segment_size=int(digitizer_time_s * sample_rate),
    segment_count=default_sequence.num_of_records() * default_params["repeats"]
)
dg.set_channel_config(channel=1, range=2)
dg.set_channel_config(channel=2, range=0.5)
dg.set_trigger_source_edge()
dg.write_configs_to_device()


## scan freq
# rf_frequencies = np.arange(-100, 150, 15)
# rf_frequencies *= ureg.kHz
# params = default_params.copy()
# for kk in range(len(rf_frequencies)):
#     params["rf"]["offset"] = rf_frequencies[kk]
#     run_experiment(params)


## scan time
start_time = time.time()
# rf_times = np.linspace(0.01, 0.2, 10)
# rf_times = np.array([0.015, 0.02, 0.03, 0.04, 0.05, 0.06, 0.07, 0.08])
# rf_times = np.array([0.02, 0.04, 0.06, 0.08])
# rf_times = np.linspace(0.001, 0.03, 20)

rf_times = np.array([0.1] * 10000)
rf_times *= ureg.ms
params = default_params.copy()

for kk in range(len(rf_times)):
    burn_chasm(params)
    params["rf"]["duration"] = rf_times[kk]
    run_experiment(params)

end_time = time.time()

print(end_time-start_time)
## empty