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
from onix.headers.pulse_tube import PulseTube
pt = PulseTube()

## function to run the experiment
def get_sequence(params):
    sequence = RFDoubleCombSatAbsSpectroscopy(params)
    return sequence


## parameters
default_params = {
    "name": "RF Comb Saturated Absorption Spectroscopy",
    "sequence_repeats_per_transfer": 10,
    "data_transfer_repeats": 1,
    "rf": {
        "pump_amplitude": 4200,  # 4200
        "probe_amplitude": 2100,  # 1100
        "pump_detunings": np.array([-65]) * ureg.kHz,  #np.arange(-70, -10, 13)
        "probe_detuning": 0 * ureg.kHz,
        "pump_time": 0.06 * ureg.ms,
        "probe_time": 0.06 * ureg.ms,
        "delay_time": 0.1 * ureg.ms,
        "probe_phase": 0,
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
scan_range = 30
scan_step = 1.5
scan_center_ref = 0
probe_amplitude_ref = 2100


## left cross
# scan_center = scan_center_ref - 167
# probe_amplitude = probe_amplitude_ref * 4
#
# probe_detunings = np.arange(scan_center - scan_range, scan_center + scan_range, scan_step)
# probe_detunings *= ureg.kHz
# params = default_params.copy()
# for kk in range(len(probe_detunings)):
#     params["rf"]["probe_detuning"] = probe_detunings[kk]
#     params["rf"]["probe_amplitude"] = probe_amplitude
#     sequence = get_sequence(params)
#     data = run_sequence(sequence, params)
#     data_id = save_data(sequence, params, *data)
#     print(data_id)
#     if first_data_id_1 == None:
#         first_data_id_1 = data_id
# last_data_id_1 = data_id
#
# for ll in range(50):
#     start_time = time.time()
#     # pt.off()
#     # time.sleep(5)
#     scan_center = scan_center_ref - 167
#
#     probe_detunings = np.arange(scan_center - scan_range, scan_center + scan_range, scan_step)
#     probe_detunings *= ureg.kHz
#     params = default_params.copy()
#     for kk in range(len(probe_detunings)):
#         params["rf"]["probe_detuning"] = probe_detunings[kk]
#         params["rf"]["probe_amplitude"] = 4200
#         sequence = get_sequence(params)
#         data = run_sequence(sequence, params)
#         data_id = save_data(sequence, params, *data)
#         # print(data_id)
#         if first_data_id_2 == None:
#             first_data_id_2 = data_id
#     last_data_id_2 = data_id
#     end_time = time.time()
#     print(
#         f"Took {(end_time-start_time):.2f} s = {(end_time-start_time) / 60:.2f} min = {(end_time-start_time) / 3600:.2f} h"
#     )
#     print(f"data = ({first_data_id_2}, {last_data_id_2})")
#     # pt.on()
#     # time.sleep(300)

## center
for ll in range(1):
    start_time = time.time()
    pt.off()
    time.sleep(5)
    scan_center = scan_center_ref

    probe_detunings = np.arange(scan_center - scan_range, scan_center + scan_range, scan_step)
    probe_detunings *= ureg.kHz
    params = default_params.copy()
    for kk in range(len(probe_detunings)):
        params["rf"]["probe_detuning"] = probe_detunings[kk]
        params["rf"]["probe_amplitude"] = 4200
        sequence = get_sequence(params)
        data = run_sequence(sequence, params)
        data_id = save_data(sequence, params, *data)
        # print(data_id)
        if first_data_id_2 == None:
            first_data_id_2 = data_id
    last_data_id_2 = data_id
    end_time = time.time()
    print(
        f"Took {(end_time-start_time):.2f} s = {(end_time-start_time) / 60:.2f} min = {(end_time-start_time) / 3600:.2f} h"
    )
    print(f"data = ({first_data_id_2}, {last_data_id_2})")
    pt.on()
    time.sleep(300)

## right cross
# scan_center = scan_center_ref + 303
# probe_amplitude = probe_amplitude_ref * 4
#
# probe_detunings = np.arange(scan_center - scan_range, scan_center + scan_range, scan_step)
# probe_detunings *= ureg.kHz
# params = default_params.copy()
# for kk in range(len(probe_detunings)):
#     params["rf"]["probe_detuning"] = probe_detunings[kk]
#     params["rf"]["probe_amplitude"] = probe_amplitude
#     sequence = get_sequence(params)
#     data = run_sequence(sequence, params)
#     data_id = save_data(sequence, params, *data)
#     print(data_id)
#     if first_data_id_3 == None:
#         first_data_id_3 = data_id
# last_data_id_3 = data_id

# for ll in range(50):
#     start_time = time.time()
#     # pt.off()
#     # time.sleep(5)
#     scan_center = scan_center_ref + 303
#
#     probe_detunings = np.arange(scan_center - scan_range, scan_center + scan_range, scan_step)
#     probe_detunings *= ureg.kHz
#     params = default_params.copy()
#     for kk in range(len(probe_detunings)):
#         params["rf"]["probe_detuning"] = probe_detunings[kk]
#         params["rf"]["probe_amplitude"] = 4200
#         sequence = get_sequence(params)
#         data = run_sequence(sequence, params)
#         data_id = save_data(sequence, params, *data)
#         # print(data_id)
#         if first_data_id_2 == None:
#             first_data_id_2 = data_id
#     last_data_id_2 = data_id
#     end_time = time.time()
#     print(
#         f"Took {(end_time-start_time):.2f} s = {(end_time-start_time) / 60:.2f} min = {(end_time-start_time) / 3600:.2f} h"
#     )
#     print(f"data = ({first_data_id_2}, {last_data_id_2})")
#     # pt.on()
#     # time.sleep(300)

## print info
# end_time = time.time()
#
# print("\n")
# print(
#     f"Took {(end_time-start_time):.2f} s = {(end_time-start_time) / 60:.2f} min = {(end_time-start_time) / 3600:.2f} h"
# )
# print(f"data = (first, last)")
# print(f"data = ({first_data_id_1}, {last_data_id_1})")
# print(f"data = ({first_data_id_2}, {last_data_id_2})")
# print(f"data = ({first_data_id_3}, {last_data_id_3})")


## empty