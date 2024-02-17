import time
from copy import deepcopy
from typing import Literal, Optional
import numpy as np
from onix.data_tools import save_experiment_data
from onix.experiments.helpers import average_data, combine_data
from onix.headers.awg.M4i6622 import M4i6622
from onix.headers.pcie_digitizer.pcie_digitizer import Digitizer
from onix.units import Q_, ureg
from onix.sequences.sequence import Sequence

try:
    m4i  # type: ignore
    print("m4i is already defined.")
except Exception:
    try:
        m4i = M4i6622()
    except Exception as e:
        m4i = None
        print("m4i is not defined with error:")
        print(e)

try:
    dg  # type: ignore
    print("dg is already defined.")
except Exception:
    try:
        dg = Digitizer()
    except Exception as e:
        dg = None
        print("dg is not defined with error:")
        print(e)

_shared_parameters = {
    "wm_channel": 5,
    "sequence_repeats_per_transfer": 1,
    "data_transfer_repeats": 1,
    "ao": {
        "name": "ao_dp",
        "order": 2,
        "center_frequency": 75 * ureg.MHz,
        "rise_delay": 1.1 * ureg.us,
        "fall_delay": 0.6 * ureg.us,
    },
    "eos": {
        "ac": {
            "name": "eo_ac",
            "amplitude": 4500,  # 4500
            "offset": -300 * ureg.MHz,
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
        "name": "rf_coil",
        "transition": "ab",
        "offset": -26.5 * ureg.kHz,
    },
    "field_plate": {
        "name": "field_plate",
        "use": False,
        "amplitude": 4500,
        "stark_shift": 2 * ureg.MHz,
        "padding_time": 5 * ureg.ms,
    },
    "chasm": {
        "transitions": ["bb"],
        "scan": 3 * ureg.MHz,
        "durations": 10 * ureg.ms,
        "repeats": 20,
        "detunings": 0 * ureg.MHz,
        "ao_amplitude": 2000,
    },
    "rf_pump": {
        "use": False,
        "into": "b",
        "amplitude": 2000,
        "scan_detunings": {
            "bbar": np.array([-130, 0]) * ureg.kHz,
            "b": np.array([0, 130]) * ureg.kHz,
            "both": np.array([-130, 130]) * ureg.kHz,
        },
    },
    "antihole": {
        "transitions": ["ac", "ca"],
        "durations": 10 * ureg.ms,
        "repeats": 20,
        "detunings": 0 * ureg.MHz,
        "ao_amplitude": 2000,
    },
    "detect": {
        "transition": "bb",
        "trigger_channel": 2,
        "ao_amplitude": 450,
        "detunings": np.linspace(-2, 2, 20) * ureg.MHz,
        "randomize": False,
        "on_time": 10 * ureg.us,
        "off_time": 2 * ureg.us,
        "cycles": {
            "chasm": 100,
            "antihole": 100,
            "rf": 100,
        },
    },
    "digitizer": {
        "sample_rate": 25e6,
        "ch1_range": 2,
        "ch2_range": 0.5,
    },
    "shutter": {
        "channel": 1,
        "rise_delay": 2 * ureg.ms,
        "fall_delay": 2 * ureg.ms,
    }
}


def update_parameters_from_shared(parameters: dict, shared_parameters=None):
    """Recursively updates undefined parameters from shared parameters."""
    if shared_parameters is None:
        shared_parameters = deepcopy(_shared_parameters)
    parameters = deepcopy(parameters)
    for kk in shared_parameters:
        if kk in parameters:
            if isinstance(parameters[kk], dict):
                update_parameters_from_shared(parameters[kk], shared_parameters[kk])
            else:
                parameters[kk] = shared_parameters[kk]
        else:
            parameters[kk] = shared_parameters[kk]
    return parameters


def setup_digitizer(
    segment_time: Q_,
    segment_repeats: int,
    sequence_repeats: int,
    num_channels: Literal[1, 2] = 2,
    ch1_range: float = 2,
    ch2_range: float = 0.5,
    sample_rate: int = 25e6,
):
    digitizer_time_s = segment_time.to("s").magnitude
    dg.set_acquisition_config(
        num_channels=num_channels,
        sample_rate=sample_rate,
        segment_size=int(digitizer_time_s * sample_rate),
        segment_count=segment_repeats * sequence_repeats,
    )
    dg.set_channel_config(channel=1, range=ch1_range)
    if num_channels > 1:
        dg.set_channel_config(channel=2, range=ch2_range)
    dg.set_trigger_source_edge()
    dg.write_configs_to_device()


def run_sequence(sequence: Sequence, params: dict, show_progress: bool = False):
    sequence.setup_sequence()
    m4i.setup_sequence(sequence)

    dg.start_capture()
    time.sleep(0.1)

    sequence_repeats_per_transfer = params["sequence_repeats_per_transfer"]
    data_transfer_repeats = params["data_transfer_repeats"]
    transmissions_avgs = []
    transmissions_errs = []
    monitors_avgs = []
    monitors_errs = []

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

        transmissions = np.array(digitizer_data[0])
        transmissions_avg, transmissions_err = average_data(
            transmissions,
            sample_rate,
            sequence.analysis_parameters["detect_pulse_times"],
        )
        monitors = np.array(digitizer_data[1])
        monitors_avg, monitors_err = average_data(
            monitors,
            sample_rate,
            sequence.analysis_parameters["detect_pulse_times"],
        )

        transmissions_avgs.append(transmissions_avg)
        transmissions_errs.append(transmissions_err)
        monitors_avgs.append(monitors_avg)
        monitors_errs.append(monitors_err)

    transmissions_avg = combine_data(transmissions_avgs)
    transmissions_err = combine_data(transmissions_errs)
    monitors_avg = combine_data(monitors_avgs)
    monitors_err = combine_data(monitors_errs)
    return transmissions_avg, transmissions_err, monitors_avg, monitors_err


def save_data(
    sequence: Sequence,
    parameters: dict,
    transmissions_avg: np.ndarray,
    transmissions_err: np.ndarray,
    monitors_avg: Optional[np.ndarray] = None,
    monitors_err: Optional[np.ndarray] = None,
):
    data = {
        "transmissions_avg": transmissions_avg,
        "transmissions_err": transmissions_err,
    }
    if monitors_avg is not None:
        data["monitors_avg"] = monitors_avg
        data["monitors_err"] = monitors_err

    headers = {
        "params": parameters,
        "detunings": sequence.analysis_parameters["detect_detunings"],
    }

    data_id = save_experiment_data(parameters["name"], data, headers)
    return data_id
