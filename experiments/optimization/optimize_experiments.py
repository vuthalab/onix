import numpy as np
from typing import Dict, List, Literal, Optional, Tuple, Union
import numbers
from onix.units import Q_, ureg

from scipy.optimize import differential_evolution
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
    antihole_avg = transmissions_avg["antihole"]
    rf_avg = transmissions_avg["rf"]
    if "chasm" in transmissions_avg:
        chasm_avg = transmissions_avg["chasm"]
        antihole_normalized = antihole_avg / chasm_avg
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

class OptimizeExperiment():
    """
    Optimize experiments using .
    """
    def __init__(self, all_params, sequence):
        self._all_params = all_params.copy()
        self._sequence = sequence
        self._var_params = []
        self._init_var_params = []
        self._bounds = []

    def set_var_param(self, var_param, bounds):
        """
        var_param: list of nested keys for 1 var or list of nested keys for 1 list var
        bounds: tuples len 2 or list of tuples
        """
        init_var_param = get_dictionary_values(self._all_params, var_param)

        if isinstance(init_var_param, numbers.Number):
            if not isinstance(bounds[0], numbers.Number) or len(bounds) > 2:
                raise ValueError(f"Incorrect bounds for {var_param}.")
            self._var_params.append(var_param)
            self._init_var_params.append(init_var_param)
            self._bounds.append(bounds)
        
        if isinstance(init_var_param, list):
            if not isinstance(bounds[0][0], numbers.Number) or np.sum([len(bounds[i]) > 2 for i in len(bounds)]):
                raise ValueError(f"Incorrect bounds for {var_param}.")
            for i, val in enumerate(init_var_param):
                self._var_params.append(var_param.append(i))
                self._init_var_params.append(init_var_param[i])
                self._bounds.append(bounds[i])

    def run_optimizer(self):
        result = differential_evolution(run_one, 
                               self._bounds, 
                               x0=self._init_var_params, 
                               atol=1e-1)
        def run_one(x):
            params = self._all_params.copy()
            for i, j in enumerate(self._init_var_params):
                match len(j):
                    case 1:
                        params[j[0]] = x[i]
                    case 2:
                        params[j[0]][j[1]] = x[i]
                    case 3:
                        params[j[0]][j[1]][j[2]] = x[i]
                    case 4:
                        params[j[0]][j[1]][j[2]][j[3]] = x[i]
                    case 5:
                        params[j[0]][j[1]][j[2]][j[3]][j[4]] = x[i]

            params["lf"]["phase_diff"] = -np.pi / 2
            data = run_sequence(self._sequence, self._all_params)
            data_id_1 = save_data(self._sequence, self._all_params, *data)

            params["lf"]["phase_diff"] = np.pi / 2
            data = run_sequence(self._sequence, self._all_params)
            data_id_2 = save_data(self._sequence, self._all_params, *data)
            
            _, ratios, _, _ = get_voltage_ratios([data_id_1, data_id_2])
            ys = 1 / ratios
            return -abs(ys[0, 0]**2 - ys[1, 0]**2)
        
        return result

