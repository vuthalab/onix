import pandas as pd
import numpy as np
import h5py
import logging
import os
from uncertainties import ufloat, unumpy

logger = logging.getLogger()
logger.setLevel(logging.INFO)
interval = 8

def h5_file_checker_getter(data, save_directory):
    indices = data.index
    stops = (np.floor(indices/interval) + 1) * interval - 1
    starts = np.floor(indices/interval) * interval
    start_stop = np.stack((starts,stops), axis=1)
    start_stop = np.unique(start_stop, axis=0)
    file_list = []
    for strt_stp in start_stop:
        with h5py.File(f"{save_directory}{int(strt_stp[0])}_{int(strt_stp[1])}.h5", "a") as f:
            pass
        file_list.append(f"{save_directory}{int(strt_stp[0])}_{int(strt_stp[1])}.h5")
    return file_list

def get_start_stop(file):
    start_stop_str, _ = file.split(("."))
    start_str, stop_str = start_stop_str.split("_")
    start = int(start_str)
    stop = int(stop_str)
    return start, stop

def get_saved_files(first, last, save_directory):
    first_ceiling = (np.floor(first/interval) + 1) * interval - 1
    first_floor = np.floor(first/interval) * interval
    last_floor = (np.floor(last/interval) + 1) * interval
    num_of_intervals = int((last_floor - first_floor + 1) / interval)
    starts = np.array([first_floor + i*interval for i in range(num_of_intervals)])
    stops = np.array([first_ceiling + i*interval for i in range(num_of_intervals)])
    start_stop = np.stack((starts, stops), axis=1)
    file_list = []
    for strt_stp in start_stop:
        file_list.append(f"{save_directory}{int(strt_stp[0])}_{int(strt_stp[1])}.h5")
    return file_list

              
def get_processed_data(first, last, save_directory):
    processed_data_files = get_saved_files(first, last, save_directory)
    load_df = pd.DataFrame()
    for file in processed_data_files:
        try:  # Do try loop if the file exists. If not, continue.
            file_name = file.rsplit('/', 1)[-1]
            start, stop = get_start_stop(file_name)
            floor = max(first, start)
            ceiling = min(last, stop)
            load_dataset = pd.read_hdf(file, key="data")
            load_dataset = load_dataset[(load_dataset.index >= floor) & (load_dataset.index <= ceiling)]
            load_df = pd.concat((load_df, load_dataset))
        except:
            continue
    return load_df

def save_processed_data(data, save_directory):
    # data is an array like object:
    first = data.index[0]    # NB: assumes that pandas dataframe is sorted by index from least to greatest
    last = data.index[-1]
    file_list = h5_file_checker_getter(data, save_directory)
    for file in file_list:
        file_name = file.rsplit('/', 1)[-1]
        start, stop = get_start_stop(file_name)
        new_data_in_this_file = data[(data.index >= start) & (data.index <= stop)]
        try:
            old_data_in_this_file = pd.read_hdf(file)
            update = pd.concat((old_data_in_this_file, new_data_in_this_file))
            update = update[~update.index.duplicated(keep='last')]
            update = update.sort_index()
            update.to_hdf(file, mode="w", key='data')
        except:
            new_data_in_this_file.to_hdf(file, mode="w", key='data')