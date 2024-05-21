import time

import numpy as np
from onix.sequences.rf_comb_sat_abs_spectroscopy import RFCombSatAbsSpectroscopy
from onix.units import ureg
from onix.experiments.shared import (
    m4i,
    dg,
    update_parameters_from_shared,
    setup_digitizer,
    run_sequence,
    save_data,
)


## function to run the experiment
def get_sequence(params):
    sequence = RFCombSatAbsSpectroscopy(params)
    return sequence


## parameters
default_params = {
    "name": "RF Comb Saturated Absorption Spectroscopy",
    "sequence_repeats_per_transfer": 20,
    "data_transfer_repeats": 1,
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
    "rf": {
        "offset": 20 * ureg.kHz, #-26.5 * ureg.kHz,
        "pump_amplitude": 250,  # 4200
        "probe_amplitude": 250,  # 1100
        "pump_detunings": np.array([-40- 167]) * ureg.kHz,  #np.arange(-70, -10, 13)
        "probe_detuning": -46 * ureg.kHz,
        "pump_time": 1.1 * ureg.ms,
        "probe_time": 1.1 * ureg.ms,
        "delay_time": 0.1 * ureg.ms,
        "probe_phase": np.pi,
    },
    "detect": {
        "detunings": np.linspace(-2.5, 2.5, 10) * ureg.MHz, # np.array([-2, 0]) * ureg.MHz,
        "on_time": 5 * ureg.us,
        "off_time": 0.5 * ureg.us,
        "cycles": {
            "chasm": 0,
            "antihole": 64,
            "rf": 64,
        },
        "delay": 8 * ureg.us,
    },
    "chasm": {
        "transitions": ["bb"], #, "rf_both"
        "scan": 2.5 * ureg.MHz,
        "durations": 50 * ureg.us,
        "repeats": 500,
        "detunings": 0 * ureg.MHz,
        "ao_amplitude": 2000,
    },
    "antihole": {
        "transitions": ["ac", "ca"], #, "rf_b" (for rf assist)
        "durations": [1 * ureg.ms, 1 * ureg.ms],
        "repeats": 20,
        "ao_amplitude": 800,
    },
    "field_plate":{
        "use": True,
        "amplitude": 3800
    }
}
default_params = update_parameters_from_shared(default_params)

default_sequence = get_sequence(default_params)
default_sequence.setup_sequence()
setup_digitizer(
    default_sequence.analysis_parameters["digitizer_duration"],
    default_sequence.num_of_record_cycles(),
    default_params["sequence_repeats_per_transfer"],
)

##
scan_range = 9
scan_step = 0.4
scan_center_ref = -40
probe_amplitude_ref = 125

num_repeats = 30
E_field = [3800, -3800]
for i in range(num_repeats):
    start_time = time.time()

    first_data_id_1 = None
    first_data_id_2 = None
    first_data_id_3 = None


    # left cross
    scan_center = scan_center_ref - 167
    probe_amplitude = probe_amplitude_ref * 4

    probe_detunings = np.arange(scan_center - scan_range, scan_center + scan_range, scan_step)
    probe_detunings *= ureg.kHz
    params = default_params.copy()
    for kk in range(len(probe_detunings)):
        params["rf"]["probe_detuning"] = probe_detunings[kk]
        params["rf"]["probe_amplitude"] = probe_amplitude

        sequence = get_sequence(params)
        data = run_sequence(sequence, params)
        data_id = save_data(sequence, params, *data)
        #print(data_id)
        if first_data_id_1 == None:
            first_data_id_1 = data_id
    last_data_id_1 = data_id


    # center
    scan_center = scan_center_ref
    probe_amplitude = probe_amplitude_ref

    probe_detunings = np.arange(scan_center - scan_range, scan_center + scan_range, scan_step)
    probe_detunings *= ureg.kHz
    params = default_params.copy()
    for kk in range(len(probe_detunings)):
        params["rf"]["probe_detuning"] = probe_detunings[kk]
        params["rf"]["probe_amplitude"] = probe_amplitude
        sequence = get_sequence(params)
        data = run_sequence(sequence, params)
        data_id = save_data(sequence, params, *data)
        #print(data_id)
        if first_data_id_2 == None:
            first_data_id_2 = data_id
    last_data_id_2 = data_id


    # right cross
    scan_center = scan_center_ref + 303
    probe_amplitude = probe_amplitude_ref * 4

    probe_detunings = np.arange(scan_center - scan_range, scan_center + scan_range, scan_step)
    probe_detunings *= ureg.kHz
    params = default_params.copy()
    for kk in range(len(probe_detunings)):
        params["rf"]["probe_detuning"] = probe_detunings[kk]
        params["rf"]["probe_amplitude"] = probe_amplitude
        sequence = get_sequence(params)
        data = run_sequence(sequence, params)
        data_id = save_data(sequence, params, *data)
        #print(data_id)
        if first_data_id_3 == None:
            first_data_id_3 = data_id
    last_data_id_3 = data_id


    # print info
    end_time = time.time()

    print("\n")
    print(
        f"Scan {i} took {(end_time-start_time):.2f} s = {(end_time-start_time) / 60:.2f} min = {(end_time-start_time) / 3600:.2f} h"
    )
    #print(f"data = (first, last)")
    print(f"Left data = ({first_data_id_1}, {last_data_id_1})")
    print(f"Center data = ({first_data_id_2}, {last_data_id_2})")
    print(f"Right data = ({first_data_id_3}, {last_data_id_3})")


## empty