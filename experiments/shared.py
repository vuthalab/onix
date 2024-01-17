import time
import numpy as np
from onix.experiments.helpers import data_averaging
from onix.data_tools import save_experiment_data
from onix.units import ureg

shared_params = {
    "wm_channel": 5,
    "repeats": 20,
    "ao": {
        "name": "ao_dp",
        "order": 2,
        "frequency": 75 * ureg.MHz,  # TODO: rename it to "center_frequency"
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
        "scan_rate": 15 * ureg.MHz / ureg.s,
        "detuning": 0 * ureg.MHz,
    }
}

def run_save_sequences(sequence, m4i, dg, params, print_progress = True):
    sequence.setup_sequence()
    m4i.setup_sequence(sequence)

    dg.start_capture()
    time.sleep(0.1)

    repeats = params["repeats"]

    for kk in range(repeats):
        if print_progress:
            print(f"{kk / repeats  * 100:.0f}%")
        m4i.start_sequence()
        m4i.wait_for_sequence_complete()
    m4i.stop_sequence()

    timeout = 1
    dg.wait_for_data_ready(timeout)
    digitizer_sample_rate, digitizer_data = dg.get_data()
    transmissions = np.array(digitizer_data[0])
    monitors = np.array(digitizer_data[1])

    # photodiode_times = [kk / digitizer_sample_rate for kk in range(len(transmissions[0]))]
    transmissions_avg, transmissions_err = data_averaging(transmissions, digitizer_sample_rate, sequence.analysis_parameters["detect_pulse_times"])
    monitors_avg, monitors_err = data_averaging(monitors, digitizer_sample_rate, sequence.analysis_parameters["detect_pulse_times"])

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

    data_id = save_experiment_data(params["name"], data, headers)
    return data_id

def update_dict_recursive(d1, d2):
    for kk in d2:
        if kk in d1:
            if isinstance(d1[kk], dict):
                update_dict_recursive(d1[kk], d2[kk])
            else:
                d1[kk] = d2[kk]
        else:
            d1[kk] = d2[kk]

def setup_digitizer(dg, repeats, default_sequence):
    digitizer_time_s = default_sequence.analysis_parameters["digitizer_duration"].to("s").magnitude
    sample_rate = 25e6
    dg.set_acquisition_config(
        num_channels=2,
        sample_rate=sample_rate,
        segment_size=int(digitizer_time_s * sample_rate),
        segment_count=default_sequence.num_of_records() * repeats,
    )
    dg.set_channel_config(channel=1, range=2)
    dg.set_channel_config(channel=2, range=0.5)
    dg.set_trigger_source_edge()
    dg.write_configs_to_device()



# another repeats to run several times, all data saved in same file
# data numbers
# parallel data saving - sub processing
            # averaging in background
