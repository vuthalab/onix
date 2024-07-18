import numpy as np
import time
from typing import Dict, List, Literal, Optional, Tuple, Union
import numbers
from onix.units import Q_, ureg
from scipy.optimize import differential_evolution, minimize
from onix.experiments.shared import (
    run_sequence,
    save_data,
)
from onix.experiments.optimization.temp import get_voltage_ratios, get_dictionary_values
from onix.sequences.lf_spectroscopy_hole import LFSpectroscopyHole
def get_sequence(params):
        sequence = LFSpectroscopyHole(params)
        return sequence

class OptimizeExperiment():
    """
    Optimize experiments using .
    """
    def __init__(self, all_params):
        self._all_params = all_params.copy()
        self._var_params = []
        self._init_var_params = []
        self._bounds = []
        self._units = []


    def set_var_param(self, var_param, bounds):
        """
        var_param: list of nested keys for 1 var or list of nested keys for 1 list var
        bounds: tuples len 2 or list of tuples
        """
        init_var_param = get_dictionary_values(self._all_params, var_param)
        print(init_var_param)
        if isinstance(init_var_param, Union[numbers.Number, Q_]):
            if not isinstance(bounds[0], numbers.Number) or len(bounds) > 2:
                raise ValueError(f"Incorrect bounds for {var_param}.")
            self._var_params.append(var_param)
            if isinstance(init_var_param, Q_):
                print("Q")
                self._units.append(1 * init_var_param.units)
                self._init_var_params.append(init_var_param.magnitude)
            else:
                print("not Q")
                self._units.append(1)
                self._init_var_params.append(init_var_param)
            self._bounds.append(bounds)
        
        if isinstance(init_var_param, list):
            if not isinstance(bounds[0][0], numbers.Number) or len(bounds[0]) > 2:
                raise ValueError(f"Incorrect bounds for {var_param}.")
            for i, val in enumerate(init_var_param):

                self._var_params.append(var_param.append(i))
                self._bounds.append(bounds[i])
                if isinstance(val, Q_):
                    self._units.append(1 * val.units)
                    self._init_var_params.append(val.magnitude)
                else:
                    self._units.append(1)
                    self._init_var_params.append(val)

    def run_optimizer(self):
        def run_one(x):
            params = self._all_params.copy()
            for i, j in enumerate(self._var_params):
                match len(j):
                    case 1:
                        params[j[0]] = x[i] * self._units[i]
                    case 2:
                        params[j[0]][j[1]] = x[i] * self._units[i]
                    case 3:
                        params[j[0]][j[1]][j[2]] = x[i] * self._units[i]
                    case 4:
                        params[j[0]][j[1]][j[2]][j[3]] = x[i] * self._units[i]
                    case 5:
                        params[j[0]][j[1]][j[2]][j[3]][j[4]] = x[i] * self._units[i]
            print(f"starting {x}")

            params["lf"]["phase_diff"] = 0
            sequence = get_sequence(params)
            time_start = time.time()
            data_1 = run_sequence(sequence, params)
            time_end = time.time()
            params["timetime"] = time_end - time_start
            data_id_1 = save_data(sequence, params, *data_1)

            params["lf"]["phase_diff"] = np.pi
            sequence = get_sequence(params)
            data_2 = run_sequence(sequence, params)
            data_id_2 = save_data(sequence, params, *data_2)
            
            print(f"({data_id_1}, {data_id_2}) with params {x}")
            _, ratios, _, _ = get_voltage_ratios([data_id_1, data_id_2])
            ys = 1 / ratios
            return -abs(ys[0, 0]**2 - ys[1, 0]**2)/(time_end-time_start)
        
        print(self._bounds)
        # result = differential_evolution(
        #     func=run_one, 
        #     bounds=self._bounds, 
        #     x0=self._init_var_params
        # )
        result = minimize(
            fun=run_one,
            x0=self._init_var_params,
            bounds=self._bounds,
        )


        return result