
import numpy as np
from onix.units import Q_, ureg

from onix.experiments.shared import (
    update_parameters_from_shared,
    setup_digitizer,
    run_sequence,
    save_data,
)

from onix.data_tools import get_experiment_data, open_analysis_folder, get_analysis_file_path
from onix.analysis.helper import group_and_average_data

def get_average_heights(data_number):
    data, headers = get_experiment_data(data_number)
    detunings_MHz = headers["detunings"].to("MHz").magnitude
    transmissions_avg = group_and_average_data(data["transmissions_avg"], headers["params"]["detect"]["cycles"])
    monitors_avg = group_and_average_data(data["monitors_avg"], headers["params"]["detect"]["cycles"])
    # antihole_avg = transmissions_avg["antihole"]
    rf_avg = transmissions_avg["rf"]
    if "chasm" in transmissions_avg:
        chasm_avg = transmissions_avg["chasm"]
        # antihole_normalized = antihole_avg / chasm_avg
        rf_normalized = rf_avg / chasm_avg
    else:
        chasm_avg = None
        #antihole_normalized = antihole_avg / monitors_avg["antihole"]
        rf_normalized = rf_avg / monitors_avg["rf"]
        antihole_normalized = rf_normalized
    if "lf" in transmissions_avg:
        lf_normalized = transmissions_avg["lf"] / monitors_avg["lf"]
    if headers["params"]["field_plate"]["use"]:
        hat_E = (headers["params"]["field_plate"]["amplitude"] > 0) == (not headers["params"]["field_plate"]["use_opposite_field"])
        hat_probe = headers["params"]["field_plate"]["stark_shift"] > 0
        mask = detunings_MHz > 0
        mask1 = detunings_MHz < 0
        if "lf" in transmissions_avg:
            return (np.array([np.average(antihole_normalized[mask]), np.average(antihole_normalized[mask1])]), 
            np.array([np.average(rf_normalized[mask]), np.average(rf_normalized[mask1])]), 
            np.array([np.average(lf_normalized[mask]), np.average(lf_normalized[mask1])]), headers, (hat_E, hat_probe))
        else:
            return np.array([
                np.average(antihole_normalized[mask]), np.average(antihole_normalized[mask1])
            ]), np.array([np.average(rf_normalized[mask]), np.average(rf_normalized[mask1])]), headers, (hat_E, hat_probe)
    else:
        return np.average(antihole_normalized), np.average(rf_normalized), headers, None
     
def get_voltage_ratios(data_list):
    ratios = []
    ratios2 = []
    headers = []
    E_fields = []
    for kk in data_list:
        h1, h2, header, E_field = get_average_heights(kk)
        ratios.append(h2)
        headers.append(header)
        E_fields.append(E_field)
    return np.ones(len(ratios)), np.array(ratios), headers, E_fields

def get_dictionary_values(dictionary, keys):
    if isinstance(keys, int):
        return dictionary[keys]
    if len(keys) == 1:
        return dictionary[keys[0]]
    return get_dictionary_values(dictionary[keys[0]], keys[1:])
