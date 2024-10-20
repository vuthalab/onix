import io
import pickle
import pint
import os.path as op
from datetime import datetime
from typing import Any, Optional

import numpy as np

from onix.units import ureg
from ._data_path import (
    get_new_experiment_path,
    get_new_persistent_path,
    get_new_analysis_folder,
    get_exist_analysis_folder,
    get_exist_experiment_path,
    get_exist_experiment_path_from_edf,
    get_exist_persistent_path,
)

pint.set_application_registry(ureg)


def _add_default_headers(headers: dict[Any, Any], data_name: str, data_number: int, edf_number: Optional[int] = None):
    """Adds default headers to be saved."""
    now = datetime.now()
    data_info = {
        "name": data_name,
        "data_number": data_number,
        "save_time": now.strftime("%Y-%m-%d %H:%M:%S"),
        "save_epoch_time": now.timestamp(),
    }
    if edf_number is not None:
        data_info["edf_number"] = edf_number
    headers["data_info"] = data_info


def _save_data(
    file_path: str,
    data: dict[Any, Any],
    data_name: str,
    data_number: int,
    headers: Optional[dict[Any, Any]] = None,
    edf_number: Optional[int] = None,
):
    """Saves data and headers in a npz file."""
    if headers is None:
        headers = {}
    _add_default_headers(headers, data_name, data_number, edf_number)
    data["__headers__"] = pickle.dumps(headers)
    np.savez(file_path, **data)


def _get_data(file_path: str) -> tuple[dict[Any, Any], dict[Any, Any]]:
    """Loads the npz file and unpickles the headers.

    Skips all custom classes that cannot be unpickled.
    """
    class DummyClass:
        pass

    class SkipAttributeErrorUnpickler(pickle._Unpickler):
        def find_class(self, __module_name: str, __global_name: str) -> Any:
            try:
                return super().find_class(__module_name, __global_name)
            except (AttributeError, ModuleNotFoundError):
                print(f"Cannot find class {__global_name} in {__module_name}. Skipping.")
                return DummyClass

    data = dict(np.load(file_path, allow_pickle=True))
    headers = SkipAttributeErrorUnpickler(io.BytesIO(data.pop("__headers__"))).load()
    return (data, headers)


def save_experiment_data(
    data_name: str, data: dict[Any, Any], headers: Optional[dict[Any, Any]] = None, edf_number: Optional[int] = None
) -> int:
    """Saves experiment data."""
    data_number, file_path = get_new_experiment_path(data_name, edf_number)
    _save_data(file_path, data, data_name, data_number, headers, edf_number)
    return data_number


def save_persistent_data(
    data_name: str, data: dict[Any, Any], headers: Optional[dict[Any, Any]] = None
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


def get_experiment_data_from_edf(edf_number: int):
    """Gets experiment data and headers."""
    file_path = get_exist_experiment_path_from_edf(edf_number)
    return _get_data(file_path)


def get_persistent_data(data_number: int, data_name: str):
    """Gets persistent data and headers."""
    file_path = get_exist_persistent_path(data_number, data_name)
    return _get_data(file_path)
