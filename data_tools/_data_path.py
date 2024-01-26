import os
import os.path as op
from datetime import datetime
from typing import List, Tuple

try:
    data_folder = os.environ["DATAFOLDER"]
except KeyError:
    raise Exception("DATAFOLDER environment variable must be defined.")
expt_folder = op.join(data_folder, "expts")
pert_folder = op.join(data_folder, "perts")
anly_folder = op.join(data_folder, "anlys")
expt_rjust = 9
pert_rjust = 9
anly_rjust = 9


def _get_current_date_directory() -> List[str]:
    """Gets ("yyyy-mm", "dd") tuple for organizing experiment data."""
    now = datetime.now()
    year = str(now.year)
    month = str(now.month).rjust(2, "0")
    day = str(now.day).rjust(2, "0")
    return (year + "_" + month, day)


def get_last_expts_data_number():
    dnum_file = op.join(expt_folder, "last_dnum")
    with open(dnum_file, "r") as f:
        try:
            last_dnum = int(f.readline())
        except ValueError:
            pass
    return last_dnum


def _increment_last_data_number(folder: str) -> int:
    """Increases the "last_dnum" file counter by 1 and returns the increased number."""
    os.makedirs(folder, exist_ok=True)
    dnum_file = op.join(folder, "last_dnum")
    if not op.exists(dnum_file) or not op.isfile(dnum_file):
        with open(dnum_file, "w") as f:
            f.write("0")

    last_dnum = 0
    with open(dnum_file, "r") as f:
        try:
            last_dnum = int(f.readline())
        except ValueError:
            pass
    last_dnum += 1
    with open(dnum_file, "w") as f:
        f.write(str(last_dnum))
    return last_dnum


def _locate_expt_data_number(data_number: int) -> Tuple[str, str]:
    """Try to find the symlink, otherwise walks through all subfolders to find an experiment file path."""
    link_folder_name = str(data_number // 100000).rjust(expt_rjust - 5, "0")
    folder = op.join(expt_folder, "links", link_folder_name)
    file = str(data_number)
    if op.exists(op.join(folder, file)):
        return (folder, file)
    
    start_str = str(data_number).rjust(expt_rjust, "0") + " - "
    with os.scandir(expt_folder) as it:
        for year_month in it:
            if year_month.is_dir():
                with os.scandir(year_month.path) as it1:
                    for day in it1:
                        if day.is_dir():
                            with os.scandir(day.path) as it2:
                                for file in it2:
                                    if file.name.startswith(start_str) and file.name.endswith(".npz"):
                                        return (os.path.join(expt_folder, year_month.name, day.name), file.name)
    raise ValueError(f"Experiment data number {data_number} is not found.")


def _locate_anly_data_number(data_number: int) -> Tuple[str, str]:
    """Walks through all subfolders to find an analysis folder path."""
    start_str = str(data_number).rjust(anly_rjust, "0") + " - "
    for path, dirs, files in os.walk(anly_folder):
        for directory in dirs:
            if directory.startswith(start_str):
                return (path, directory)
    raise ValueError(f"Analysis data number {data_number} is not found.")


def get_new_experiment_path(data_name: str) -> Tuple[int, str]:
    """Gets the data number and file path for new experiment data.
    
    Also creates a symlink pointing to the file.
    """
    year_month, day = _get_current_date_directory()
    data_number = _increment_last_data_number(expt_folder)
    folder = op.join(expt_folder, year_month, day)
    os.makedirs(folder, exist_ok=True)
    file_name = str(data_number).rjust(expt_rjust, "0") + " - " + data_name + ".npz"

    link_folder_name = str(data_number // 100000).rjust(expt_rjust - 5, "0")
    link_folder = op.join(expt_folder, "links", link_folder_name)
    os.makedirs(link_folder, exist_ok=True)
    os.symlink(op.join(folder, file_name), op.join(link_folder, str(data_number)))
    return (data_number, op.join(folder, file_name))


def get_new_persistent_path(data_name: str) -> Tuple[int, str]:
    """Gets the data number and file path for new persistent data."""
    folder = op.join(pert_folder, data_name)
    data_number = _increment_last_data_number(folder)
    file_name = str(data_number).rjust(pert_rjust, "0") + " - " + data_name + ".npz"
    return (data_number, op.join(folder, file_name))


def get_new_analysis_folder(data_name: str) -> Tuple[int, str]:
    """Creates and returns a new folder for storing analysis files."""
    year_month, day = _get_current_date_directory()
    data_number = _increment_last_data_number(anly_folder)
    folder_name = str(data_number).rjust(anly_rjust, "0") + " - " + data_name
    folder = op.join(anly_folder, year_month, day, folder_name)
    os.makedirs(folder, exist_ok=True)
    return (data_number, folder)


def get_exist_experiment_path(data_number: int) -> str:
    """Gets the file path for existing experiment data."""
    parent, file_name = _locate_expt_data_number(data_number)
    return op.join(parent, file_name)


def get_exist_persistent_path(data_number: int, data_name: str) -> str:
    """Gets the file path for existing persistent data."""
    folder = op.join(pert_folder, data_name)
    file_name = str(data_number).rjust(pert_rjust, "0") + " - " + data_name + ".npz"
    return op.join(folder, file_name)

def get_exist_analysis_folder(data_number: int) -> str:
    """Gets the folder for existing analysis data."""
    parent, folder = _locate_anly_data_number(data_number)
    return op.join(parent, folder)
