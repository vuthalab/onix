import copy
from typing import Any

from onix.control import save_edf


class ExpDefinitionCreator:
    def __init__(self, name, exp_sequence, parameters):
        self._name = name
        self._exp_sequence = exp_sequence
        self._parameters = parameters

    def _get_parameter_after_iteration(
        self,
        parameters_to_iterate,
        iterate_parameter_values,
        iteration_index: int
    ) -> dict[str, Any]:
        parameters = copy.deepcopy(self._parameters)
        for kk, parameter_to_iterate in enumerate(parameters_to_iterate):
            parameters_path = parameters
            for parameter_step in parameter_to_iterate[:-1]:
                parameters_path = parameters_path[parameter_step]
            parameters_path[parameter_to_iterate[-1]] = iterate_parameter_values[iteration_index][kk]
        return parameters

    def _build_edf(
        self,
        parameters_to_iterate = None,
        iterate_parameter_values = None,
        iterate_index = None,
        skip_awg_programming = False,
        skip_digitizer_programming = False,
    ):
        if parameters_to_iterate is None:
            parameters = self._parameters
            skip_awg_programming = False
            skip_digitizer_programming = False
            run_first_card_only = False
        else:
            parameters = self._get_parameter_after_iteration(
                parameters_to_iterate,
                iterate_parameter_values,
                iterate_index,
            )
            if iterate_index == 0:
                run_first_card_only = False
            else:
                run_first_card_only = True
            if iterate_index == len(iterate_parameter_values) - 1:
                stop_first_card_only = False
            else:
                stop_first_card_only = True

        return {
            "name": self._name,
            "exp_sequence": self._exp_sequence,
            "parameters": parameters,
            "parameters_to_iterate": parameters_to_iterate,
            "iterate_parameter_values": iterate_parameter_values,
            "skip_awg_programming": skip_awg_programming,
            "skip_digitizer_programming": skip_digitizer_programming,
            "run_first_card_only": run_first_card_only,
            "stop_first_card_only": stop_first_card_only,
        }

    def schedule(self, repeats: int = 1):
        edf_ids = []
        for kk in range(repeats):
            edf_ids.append(save_edf(self._build_edf()))
        print(f"Scheduled {self._name} experiment for {repeats} times: ", end="")
        if len(edf_ids) > 1:
            print(f"EDF #{edf_ids[0]} - {edf_ids[-1]}.")
        else:
            print(f"EDF #{edf_ids[0]}.")

    def iterate_parameters(
        self,
        parameters_to_iterate = None,
        iterate_parameter_values = None,
        repeats: int = 1,
    ):
        if repeats <= 0:
            raise ValueError("Repeats must be greater than 0.")
        edf_ids = []
        for kk in range(len(iterate_parameter_values)):
            if kk == 0:
                skip_awg_programming = False
                skip_digitizer_programming = False
            else:
                skip_awg_programming = True
                skip_digitizer_programming = True
            edf_id = save_edf(
                self._build_edf(
                    parameters_to_iterate = parameters_to_iterate,
                    iterate_parameter_values = iterate_parameter_values,
                    iterate_index = kk,
                    skip_awg_programming = skip_awg_programming,
                    skip_digitizer_programming = skip_digitizer_programming,
                )
            )
            edf_ids.append(edf_id)
        print(f"Iterate parameters for {self._name} experiment for {len(iterate_parameter_values)} values: ", end="")
        if len(edf_ids) > 1:
            print(f"EDF #{edf_ids[0]} - {edf_ids[-1]}. ", end="")
        else:
            print(f"EDF #{edf_ids[0]}. ", end="")
        for ll in range(repeats - 1):
            edf_ids = []
            for kk in range(len(iterate_parameter_values)):
                skip_awg_programming = True
                skip_digitizer_programming = True
                edf_id = save_edf(
                    self._build_edf(
                        parameters_to_iterate = parameters_to_iterate,
                        iterate_parameter_values = iterate_parameter_values,
                        iterate_index = kk,
                        skip_awg_programming = skip_awg_programming,
                        skip_digitizer_programming = skip_digitizer_programming,
                    )
                )
                edf_ids.append(edf_id)
        print(f"Last EDF is #{edf_ids[-1]}.")
            