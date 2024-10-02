import pickle
import os as _os

import numpy as np
import pandas as pd

from typing import Any, Optional
from onix.data_tools import data_folder as _data_folder
from onix.units import ureg, Q_

edf_folder = _os.path.join(_data_folder, "expt_defs")
_edf_next_save_number_file = _os.path.join(edf_folder, "next_save_number")
_edf_next_run_number_file = _os.path.join(edf_folder, "next_run_number")


def _get_next_save_edf_number() -> int:
    next_save_number = 0
    if _os.path.isfile(_edf_next_save_number_file):
        with open(_edf_next_save_number_file, "r") as f:
            next_save_number = int(f.readline())
    return next_save_number


def _get_next_run_edf_number() -> int:
    next_run_number = 0
    if _os.path.isfile(_edf_next_run_number_file):
        with open(_edf_next_run_number_file, "r") as f:
            next_run_number = int(f.readline())
    return next_run_number


def save_edf(edf_dict: dict) -> int:
    # This function is not thread / process safe. If this function is called simultaneously an error may occur.
    next_save_number = _get_next_save_edf_number()
    with open(_os.path.join(edf_folder, f"{next_save_number}_edf.pkl"), "wb") as f:
        pickle.dump(edf_dict, f)
    next_save_number += 1
    with open(_edf_next_save_number_file, "w") as f:
        f.write(str(next_save_number))
    return next_save_number - 1


def try_get_next_edf_to_run() -> tuple[int, Any]:
    # This function is not thread / process safe. If this function is called simultaneously an error may occur.
    try:
        next_save_number = _get_next_save_edf_number()
    except ValueError:
        next_save_number = _get_next_save_edf_number()
    original_next_run_number = _get_next_run_edf_number()
    next_run_number = original_next_run_number
    edf_dict = None
    while next_run_number < next_save_number:
        next_run_number += 1
        if _os.path.isfile(_os.path.join(edf_folder, f"{next_run_number - 1}_edf.pkl")):
            with open(_os.path.join(edf_folder, f"{next_run_number - 1}_edf.pkl"), "rb") as f:
                edf_dict = pickle.load(f)
            break
    if original_next_run_number != next_run_number:
        with open(_edf_next_run_number_file, "w") as f:
            f.write(str(next_run_number))
    return (next_run_number - 1, edf_dict)


def clear_pending_edfs():
    next_save_number = _get_next_save_edf_number()
    with open(_edf_next_run_number_file, "w") as f:
        f.write(str(next_save_number))
    

_valid_iterator_types = (
    list, np.ndarray, pd.Series
)  # excludes dict, set, str, bytes, etc.


def list_to_array(l, units: Optional[str] = None):
    """Converts a list to an Quantity array with the units properly handled."""
    if isinstance(l, Q_):
        return l
    
    if units is not None:
        units = getattr(ureg, units)
    first_element = l[0]
    if isinstance(first_element, Q_):
        first_element = l[0]
        units = first_element.units
    if units is None:
        return np.array(l)
    else:
        values = [e.to(units).magnitude for e in l]
        return np.array(values) * units


def unify_lists(*args, length: Optional[int] = None):
    """Unify variables to the same length of lists.
    
    If an variable is a single value (instead of a list), it is promoted to a
    list with N repeats of the same value, where N is the length of the list.
    If length is not given, it goes through the variables to find a list and use its length.
    If two lists of different lengths are given, it raises an error.
    """
    # checks if any variable in args is already a list.
    for l in args:
        if isinstance(l, _valid_iterator_types):
            l_length = len(l)
            if length is None:
                length = l_length
            elif length != l_length:
                raise ValueError(f"data {l} cannot be unified to the same length = {length}.")
        if isinstance(l, Q_):
            try:
                l_length = len(l)
                if length is None:
                    length = l_length
                elif length != l_length:
                    raise ValueError(f"data {l} cannot be unified to the same length = {length}.")
            except TypeError as e:
                pass

    if length is None:
        length = 1

    # converts all variables to lists of the same length.
    return_vals = []
    for l in args:
        if isinstance(l, _valid_iterator_types):
            return_vals.append(l)
        elif isinstance(l, Q_):
            try:
                l[0]
                return_vals.append(l)
            except TypeError as e:
                return_vals.append([l for kk in range(length)])

        else:
            return_vals.append([l for kk in range(length)])

    return_vals = [list_to_array(l) for l in return_vals]
    return tuple(return_vals)


def bin_and_average_absorption_data(
    data: np.ndarray,
    sample_rate: float,
    pulse_times: list[tuple[float, float]]
) -> np.ndarray:
    """Averages digitizer data using time intervals.

    Args:
        data: np.array, must be 2-dimensional. The first dimension is repeats (segments).
            The second dimension is time indices.
        sample_rate: float, sample rate per second.
        pulse_times: list of 2-tuples, time intervals to average the data at.

    Returns:
        data_avg
        data_avg has the first dimension as repeats,
        and the second dimension as time interval indices (same length as pulse_times).
    """
    if not isinstance(data, np.ndarray):
        data = np.array(data)
    if not (data.ndim == 2):
        raise ValueError("The input data must be 2-dimensional")

    data_avg = []

    pulse_times = (np.array(pulse_times) * sample_rate).astype(int)
    for kk in range(len(pulse_times)):
        data_per_pulse = data[:, pulse_times[kk][0]: pulse_times[kk][1]]
        scans_avg = np.average(data_per_pulse, axis=1)
        data_avg.append(scans_avg)

    return np.transpose(data_avg)


def group_data_by_detects(
    data: np.ndarray, detect_repeats: dict[str, int]
) -> dict[str, np.ndarray]:
    current_index = 0
    grouped_data = {}
    for name in detect_repeats:
        repeats = detect_repeats[name]
        grouped_data[name] = data[current_index: current_index + repeats]
        current_index += repeats
    if current_index != len(data):
        raise ValueError(f"Obtained data length {len(data)} does not agree with the number of detects {current_index}.")
    return grouped_data
