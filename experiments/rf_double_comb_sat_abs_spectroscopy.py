import time

import numpy as np
from onix.sequences.rf_double_comb_sat_abs_spectroscopy import RFDoubleCombSatAbsSpectroscopy
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
    sequence = RFDoubleCombSatAbsSpectroscopy(params)
    return sequence


## parameters
default_params = {
    "name": "RF Comb Saturated Absorption Spectroscopy",
    "sequence_repeats_per_transfer": 20,
    "data_transfer_repeats": 1,
    "rf": {
        "offset": 20 * ureg.kHz, #-26.5 * ureg.kHz,
        "pump_amplitude": 1000,  # 4200
        "probe_amplitude": 125,  # 1100
        "pump_detunings": np.array([-40- 167]) * ureg.kHz,  #np.arange(-70, -10, 13)
        "probe_detunings": np.array([-40- 167]) * ureg.kHz,  #np.arange(-70, -10, 13)
        "pump_time": 0.8 * ureg.ms,
        "probe_time": 1.6 * ureg.ms,
        "delay_time": 0.1 * ureg.ms,
        "probe_phase": np.pi,
    },
}
default_params = update_parameters_from_shared(default_params)

default_sequence = get_sequence(default_params)
default_sequence.setup_sequence()
setup_digitizer(
    default_sequence.analysis_parameters["digitizer_duration"],
    default_sequence.num_of_record_cycles(),
    default_params["sequence_repeats_per_transfer"],
)


## timeit
start_time = time.time()

first_data_id_1 = None
first_data_id_2 = None
first_data_id_3 = None


## scan
scan_range = 3
scan_step = 0.5
scan_center_ref = -40
probe_amplitude_ref = 125


## left cross
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
    print(data_id)
    if first_data_id_1 == None:
        first_data_id_1 = data_id
last_data_id_1 = data_id


## center
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
    print(data_id)
    if first_data_id_2 == None:
        first_data_id_2 = data_id
last_data_id_2 = data_id


## right cross
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
    print(data_id)
    if first_data_id_3 == None:
        first_data_id_3 = data_id
last_data_id_3 = data_id


## print info
end_time = time.time()

print("\n")
print(
    f"Took {(end_time-start_time):.2f} s = {(end_time-start_time) / 60:.2f} min = {(end_time-start_time) / 3600:.2f} h"
)
print(f"data = (first, last)")
print(f"data = ({first_data_id_1}, {last_data_id_1})")
print(f"data = ({first_data_id_2}, {last_data_id_2})")
print(f"data = ({first_data_id_3}, {last_data_id_3})")


## empty