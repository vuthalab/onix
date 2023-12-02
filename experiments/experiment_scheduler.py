import importlib
import subprocess
import pickle
from typing import Any


class SchedulerBackend:
    def __init__(self):
        self._experiments = {}

    def add_experiment(self, name: str, path: str):
        self._experiments[name] = path

    def run_experiment(self, name: str, overriden_parameters: dict[str, Any] = None):
        if name not in self._experiments:
            raise ValueError(f"Experiment {name} is not defined.")
        if overriden_parameters is None:
            overriden_parameters = {}
        data_to_subprocess = pickle.dumps(overriden_parameters)
