from copy import deepcopy
from typing import Any, Dict, Tuple

import numpy as np


class _Parameter:
    @classmethod
    def from_tuple(param_tuple: Tuple[str, Any]):
        if param_tuple[0] == "scan":
            return _Scan(*param_tuple[1])
        else:
            raise ValueError("Parameter type {param_tuple[0]} is not supported.")

    @property
    def value(self):
        raise NotImplementedError()


class _Scan(_Parameter):
    def __init__(
        self, scan_min: float, scan_max: float, scan_steps: int, randomize: bool
    ):
        self._scan_min = scan_min
        self._scan_max = scan_max
        self._scan_steps = scan_steps
        self._randomize = randomize

    @property
    def value(self):
        val = np.linspace(self._scan_min, self._scan_max, self._scan_steps)
        if self._randomize:
            np.random.shuffle(val)
        return val


def get_parameters(param_file: str) -> Dict[str, Any]:
    return exec(open(param_file).read())


def parse_parameters(params: Dict[str, Any]):
    parsed_params = deepcopy(params)
    for name in parsed_params:
        raw_param = parsed_params[name]
        if isinstance(raw_param, tuple) and len(raw_param) == 2:
            try:
                parameter = _Parameter.from_tuple(raw_param).value
            except Exception:
                parameter = raw_param
            parsed_params[name] = parameter
