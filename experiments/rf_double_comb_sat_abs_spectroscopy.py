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
        "pump_amplitude": 1050,  # 4200
        "probe_amplitude": 1050,  # 1100
        "pump_detunings": np.array([-65]) * ureg.kHz,  #np.arange(-70, -10, 13)
        "probe_detuning": 0 * ureg.kHz,
        "pump_time": 0.28 * ureg.ms,
        "probe_time": 0.28 * ureg.ms,
        "delay_time": 0.1 * ureg.ms,
        "probe_phase": 0,
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
    "field_plate": {
        "name": "field_plate",
        "use": True,
        "amplitude": 4500,
        "stark_shift": 2 * ureg.MHz,
        "padding_time": 0 * ureg.ms,
    },
    "digitizer": {
        "sample_rate": 25e6,
        "ch1_range": 2,
        "ch2_range": 0.5,
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




## scan
scan_range = 30
scan_step = 1.2
scan_center_ref = 0
probe_amplitude_ref = 500


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
very_first = None
for ll in range(250):
    for field_plate_amplitude in [-4500, 4500]:
        print("----------------------------")
        print(f"field plate amplitude = {field_plate_amplitude}")
        first_data_id_1 = None
        first_data_id_2 = None
        first_data_id_3 = None
        start_time = time.time()
        scan_range = 8
        scan_step = 1
        scan_center = scan_center_ref - 167
        probe_detunings = np.arange(scan_center - scan_range, scan_center + scan_range, scan_step)
        probe_detunings *= ureg.kHz
        params = default_params.copy()
        for kk in range(len(probe_detunings)):
            params["field_plate"]["amplitude"] = field_plate_amplitude
            params["rf"]["probe_detuning"] = probe_detunings[kk]
            params["rf"]["probe_amplitude"] = 1050 * 4
            sequence = get_sequence(params)
            data = run_sequence(sequence, params)
            data_id = save_data(sequence, params, *data)
            if first_data_id_1 == None:
                first_data_id_1 = data_id
            if very_first == None:
                very_first = data_id
        last_data_id_1 = data_id
        end_time = time.time()
        print(
            f"Left took {(end_time-start_time):.2f} s = {(end_time-start_time) / 60:.2f} min = {(end_time-start_time) / 3600:.2f} h -- data = ({first_data_id_1}, {last_data_id_1})"
        )

    ## center

        start_time = time.time()
        scan_range = 4
        scan_step = 0.5
        scan_center = scan_center_ref
        probe_detunings = np.arange(scan_center - scan_range, scan_center + scan_range, scan_step)
        probe_detunings *= ureg.kHz
        params = default_params.copy()
        for kk in range(len(probe_detunings)):
            params["field_plate"]["amplitude"] = field_plate_amplitude
            params["rf"]["probe_detuning"] = probe_detunings[kk]
            params["rf"]["probe_amplitude"] = 1050 * 1
            sequence = get_sequence(params)
            data = run_sequence(sequence, params)
            data_id = save_data(sequence, params, *data)
            if first_data_id_2 == None:
                first_data_id_2 = data_id
        last_data_id_2 = data_id
        end_time = time.time()
        print(
            f"Center took {(end_time-start_time):.2f} s = {(end_time-start_time) / 60:.2f} min = {(end_time-start_time) / 3600:.2f} h -- data = ({first_data_id_2}, {last_data_id_2})"
        )

print(very_first)
## right
        # start_time = time.time()
        # scan_range = 12
        # scan_step = 1.1
        # scan_center = scan_center_ref + 303
        # probe_detunings = np.arange(scan_center - scan_range, scan_center + scan_range, scan_step)
        # probe_detunings *= ureg.kHz
        # params = default_params.copy()
        # for kk in range(len(probe_detunings)):
        #     params["field_plate"]["amplitude"] = field_plate_amplitude
        #     params["rf"]["probe_detuning"] = probe_detunings[kk]
        #     params["rf"]["probe_amplitude"] = 1050 * 4
        #     sequence = get_sequence(params)
        #     data = run_sequence(sequence, params)
        #     data_id = save_data(sequence, params, *data)
        #     if first_data_id_3 == None:
        #         first_data_id_3 = data_id
        # last_data_id_3 = data_id
        # end_time = time.time()
        # print(
        #     f"Right transition took {(end_time-start_time):.2f} s = {(end_time-start_time) / 60:.2f} min = {(end_time-start_time) / 3600:.2f} h"
        # )
        # print(f"data = ({first_data_id_3}, {last_data_id_3})")

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


# FOR reversed e field
#
# start_time = time.time()
#
# first_data_id_1 = None
# first_data_id_2 = None
# first_data_id_3 = None
#
#
# scan_range = 30
# scan_step = 1.5
# scan_center_ref = 0
# probe_amplitude_ref = 2100
#
#
# for ll in range(20):
#     start_time = time.time()
#     pt.off()
#     time.sleep(5)
#     scan_range = 10
#     scan_step = 1
#     scan_center = scan_center_ref - 167
#     probe_detunings = np.arange(scan_center - scan_range, scan_center + scan_range, scan_step)
#     probe_detunings *= ureg.kHz
#     params = default_params.copy()
#     for kk in range(len(probe_detunings)):
#         params["field_plate"]["amplitude"] = -4500
#         params["rf"]["probe_detuning"] = probe_detunings[kk]
#         # params["rf"]["probe_amplitude"] = 4200
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
#     pt.on()
#     time.sleep(200)
#
# for ll in range(20):
#     start_time = time.time()
#     pt.off()
#     time.sleep(5)
#     scan_range = 10
#     scan_step = 1.5
#     scan_center = scan_center_ref
#     probe_detunings = np.arange(scan_center - scan_range, scan_center + scan_range, scan_step)
#     probe_detunings *= ureg.kHz
#     params = default_params.copy()
#     for kk in range(len(probe_detunings)):
#         params["field_plate"]["amplitude"] = -4500
#         params["rf"]["probe_detuning"] = probe_detunings[kk]
#         # params["rf"]["probe_amplitude"] = 4200
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
#     pt.on()
#     time.sleep(200)