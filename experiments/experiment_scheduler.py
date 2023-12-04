import signal
import subprocess
import sys
import threading
import time
from typing import Any, Union

import zmq

PORT = 38573


class SchedulerBackend:
    def __init__(self):
        self._experiments = {}
        self._experiment_rid = 0
        self._queued_experiments = {}
        self._previous_experiments = {}
        self._socket_port = None
        self._current_rid = None
        self._current_subprocess = None
        
        self._server_thread = threading.Thread(target=self._server_worker, daemon=True)
        self._server_thread.start()
        
        self._experiment_thread = threading.Thread(target=self._experiment_worker, daemon=True)
        self._experiment_thread.start()

    def _server_worker(self):
        context = zmq.Context()
        self._socket = context.socket(zmq.REP)
        self._socket_port = self._socket.bind(f"tcp://*:{PORT}")
        while True:
            try:
                command, data = self._socket.recv_pyobj()
                if command == "parameters":
                    rid = data
                    self._socket.send_pyobj(self._previous_experiments[rid][2])
                elif command == "queue":
                    name = data[0]
                    overriden_parameters = data[1]["overriden_parameters"]
                    self._socket.send_pyobj(self.queue_experiment(name, overriden_parameters))
                elif command == "list_queue":
                    self._socket.send_pyobj(self._queued_experiments)
                elif command == "list_previous":
                    self._socket.send_pyobj(self._previous_experiments)
                elif command == "cancel":
                    rid = data
                    self._socket.send_pyobj(self.cancel_experiment(rid))
                elif command == "cancel_current":
                    self._socket.send_pyobj(self.cancel_experiment(self._current_rid))
                elif command == "cancel_all":
                    self._socket.send_pyobj(self.cancel_all_experiments())
                else:
                    raise NotImplemented(f"{command} is not defined.")
            except Exception as e:
                print(e)
            time.sleep(0.01)

    def _execute_subprocess(self, rid: int):
        name = self._queued_experiments[rid][0]
        path = self._queued_experiments[rid][1]
        self._previous_experiments[rid] = self._queued_experiments.pop(rid)
        print(f"Experiment #{rid} of {name} started")
        self._current_rid = rid
        self._current_subprocess: Union[subprocess.Popen, None] = subprocess.Popen(
            [
                sys.executable,
                path,
                "--rid",
                str(rid),
                "--port",
                str(self._socket_port),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )

    def _experiment_worker(self):
        while True:
            if not self._current_subprocess and self._current_subprocess.poll():
                print(f"Experiment #{self._current_rid} finished.")
                self._current_subprocess = None
            if not self._current_subprocess:
                if self._queued_experiments:
                    self._execute_subprocess(self._queued_experiments.keys[0])
            time.sleep(0.01)

    def add_experiment(self, name: str, path: str):
        self._experiments[name] = path

    def queue_experiment(self, name: str, overriden_parameters: dict[str, Any] = None):
        if name not in self._experiments:
            raise ValueError(f"Experiment {name} is not defined.")
        path = self._experiments[name]
        if overriden_parameters is None:
            overriden_parameters = {}

        data_to_subprocess = {}
        data_to_subprocess["overriden"] = overriden_parameters
        rid = self._experiment_rid
        self._queued_experiments[rid] = (
            name, path, data_to_subprocess
        )
        self._experiment_rid += 1
        return rid

    def cancel_experiment(self, rid: int):
        if rid in self._queued_experiments:
            self._queued_experiments.pop(rid)
        elif rid == self._current_rid:
            if self._current_subprocess:
                self._current_subprocess.send_signal(signal.SIGINT)
            else:
                print(f"Experiment #{rid} was already cancelled.")

    def cancel_all_experiments(self):
        self._queued_experiments = {}
        self.cancel_experiment(self._current_rid)
