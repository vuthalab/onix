import time
import os

import numpy as np

os.chdir("/home/onix/gdrive/code/onix_control/new")
os.environ["DATAFOLDER"] = "/home/onix/Desktop/data"

from data_tools import save_experiment_data
from sequences.rabi_flop import RabiFlop
from sequences.aom_settings import aoms

from headers.digitizer import Digitizer
from headers.awg_header.M4i6622 import M4i6622
from headers.highfinesse_wavemeter_v4.wavemeter import WM
from units import ureg

## experiment parameters
parameters = {
    "probe_channel": "bb",
    "burn_width": 1 * ureg.MHz,
    "burn_time": 1 * ureg.s,
    "pump_time": 100 * ureg.ms,
    "probe_scan_range": 0.5 * ureg.MHz,
    "probe_scan_number": 11,
    "probe_amplitude": 400,
    "probe_on_time": 12 * ureg.us,
    "probe_off_time": 4 * ureg.us,
    "probe_repeats": 2,
    "ttl_start_time": 12 * ureg.us,
    "ttl_duration": 4 * ureg.us,
    "sequence_ttl_offset_time": 4 * ureg.us,
}
constants = {
    "digitizer_sampling_rate": 10e6,
}

probe_center = aoms[parameters["probe_channel"]].center_frequency
probe_frequencies = np.linspace(
    probe_center - parameters["probe_scan_range"],
    probe_center - parameters["probe_scan_range"],
    parameters["probe_scan_number"],
)

## build sequence
sequence = RabiFlop(parameters["probe_channel"])
sequence.add_burns(parameters["burn_width"], parameters["burn_time"])
sequence.add_pumps(parameters["pump_time"])
digitizer_record_duration = sequence.add_probe(
    probe_frequencies,
    parameters["probe_amplitude"],
    parameters["probe_on_time"],
    parameters["probe_off_time"],
    parameters["ttl_start_time"],
    parameters["ttl_duration"],
    parameters["sequence_ttl_offset_time"],
)
sequence.add_break()
sequence.setup_sequence(parameters["probe_repeats"])

## setup digitizer
dg = Digitizer("192.168.0.125")
dg_params = {
    "num_samples": digitizer_record_duration / constants["digitizer_sampling_rate"],
    "sampling_rate": constants["digitizer_sampling_rate"],
    "ch1_voltage_range": 2,
    "ch2_voltage_range": 2,
    "trigger_channel": 0, # 1 -> ch1, 2 -> ch2, 0 -> ext, else -> immediate
    "data_format": "float32",
    "coupling": "DC",
    "num_records": 3 * parameters["probe_repeats"],
    "triggers_per_arm": 1,
}

wavemeter = WM()