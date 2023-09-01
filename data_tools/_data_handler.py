import io
import os
import pickle
import os.path as op
from datetime import datetime
from typing import Any, Dict, Tuple, Optional

import numpy as np

from ._data_path import (
    get_new_experiment_path,
    get_new_persistent_path,
    get_new_analysis_folder,
    get_exist_analysis_folder,
    get_exist_experiment_path,
    get_exist_persistent_path,
    get_analysis_info_path,
    get_experiment_info_path,
)
from ._data_info import (
    get_data_info,
    save_data_info,
)


def _add_default_headers(headers: Dict[Any, Any], data_name: str, data_number: int):
    """Adds default headers to be saved."""
    now = datetime.now()
    data_info = {
        "name": data_name,
        "data_number": data_number,
        "save_time": now.strftime("%Y-%m-%d %H:%M:%S"),
        "save_epoch_time": now.timestamp(),
    }
    headers["data_info"] = data_info


def _save_data(
    file_path: str,
    data: Dict[Any, Any],
    data_name: str,
    data_number: int,
    headers: Optional[Dict[Any, Any]] = None,
):
    """Saves data and headers in a npz file."""
    if headers is None:
        headers = {}
    _add_default_headers(headers, data_name, data_number)
    data["__headers__"] = pickle.dumps(headers)
    np.savez(file_path, **data)


def _get_date_from_path(data_file_path: str):
    day_folder = os.path.dirname(data_file_path)
    day = os.path.basename(day_folder)
    year_month = os.path.basename(os.path.dirname(day_folder))
    year, month = year_month.split("_")
    return (int(year), int(month), int(day))


def _save_data_info(
    info_file_path: str,
    data_number: int,
    data_file_path: str,
    info: Dict[str, Any],
):
    data_info = get_data_info(info_file_path)
    year, month, day = _get_date_from_path(data_file_path)
    data_info[data_number] = {
        "year": year,
        "month": month,
        "day": day,
    }
    data_info[data_number].update(info)
    save_data_info(info_file_path, data_info)


def _get_data(file_path: str) -> Tuple[Dict[Any, Any], Dict[Any, Any]]:
    """Loads the npz file and unpickles the headers.

    Skips all custom classes that cannot be unpickled.
    """
    class DummyClass:
        pass

    class SkipAttributeErrorUnpickler(pickle._Unpickler):
        def find_class(self, __module_name: str, __global_name: str) -> Any:
            try:
                return super().find_class(__module_name, __global_name)
            except AttributeError:
                print(f"Cannot find class {__global_name} in {__module_name}. Skipping.")
                return DummyClass

    data = dict(np.load(file_path))
    headers = SkipAttributeErrorUnpickler(io.BytesIO(data.pop("__headers__"))).load()
    return (data, headers)


def save_experiment_data(
    data_name: str, data: Dict[Any, Any], headers: Optional[Dict[Any, Any]] = None
) -> int:
    """Saves experiment data."""
    data_number, file_path = get_new_experiment_path(data_name)
    _save_data(file_path, data, data_name, data_number, headers)
    return data_number


def save_persistent_data(
    data_name: str, data: Dict[Any, Any], headers: Optional[Dict[Any, Any]] = None
) -> int:
    """Saves persistent data."""
    data_number, file_path = get_new_persistent_path(data_name)
    _save_data(file_path, data, data_name, data_number, headers)
    return data_number


def open_analysis_folder(data_name: str) -> int:
    """Opens an analysis file for saving data."""
    data_number, folder_path = get_new_analysis_folder(data_name)
    return data_number


def get_analysis_file_path(data_number: int, file_name: str) -> str:
    """Gets path to an analysis file."""
    parent = get_exist_analysis_folder(data_number)
    return op.join(parent, file_name)


def get_experiment_data(data_number: int):
    """Gets experiment data and headers."""
    file_path = get_exist_experiment_path(data_number)
    return _get_data(file_path)


def get_persistent_data(data_number: int, data_name: str):
    """Gets persistent data and headers."""
    file_path = get_exist_persistent_path(data_number, data_name)
    return _get_data(file_path)
