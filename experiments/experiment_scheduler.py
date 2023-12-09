import signal
import subprocess
import sys
import threading
import time
from typing import Any, Union
from PyQt5 import QtWidgets, QtGui, QtCore

import zmq

PORT = 38573


class SchedulerBackend:
    def __init__(self):
        self._socket = None
        self._socket_port = PORT
        self._experiments = {}
        self._experiment_rid = 0
        self._queued_experiments = {}
        self._previous_experiments = {}
        self._current_experiment = None
        self._current_rid = None
        self._current_subprocess = None
        self._last_update_time = time.time()
        
        self._server_thread = threading.Thread(target=self._server_worker, daemon=True)
        self._server_thread.start()
        
        self._experiment_thread = threading.Thread(target=self._experiment_worker, daemon=True)
        self._experiment_thread.start()

    def _server_worker(self):
        context = zmq.Context()
        self._socket = context.socket(zmq.REP)
        self._socket.bind(f"tcp://*:{PORT}")
        while True:
            try:
                command, data = self._socket.recv_pyobj()
                if command == "parameters":
                    rid = data
                    if self._current_experiment is not None and rid == self._current_rid:
                        self._socket.send_pyobj(self._current_experiment[2])
                    else:
                        self._socket.send_pyobj(None)
                elif command == "queue":
                    name = data[0]
                    overriden_parameters = data[1]["overriden_parameters"]
                    self._socket.send_pyobj(self.queue_experiment(name, overriden_parameters))
                elif command == "list_queue":
                    self._socket.send_pyobj(self._queued_experiments)
                elif command == "list_previous":
                    self._socket.send_pyobj(self._previous_experiments)
                elif command == "get_current":
                    self._socket.send_pyobj(self._current_experiment)
                elif command == "cancel":
                    rid = data
                    if rid != self._current_rid:
                        self._socket.send_pyobj(self.cancel_current_experiment())
                    elif rid in self._queued_experiments:
                        self._socket.send_pyobj(self.cancel_queued_experiment(rid))
                elif command == "cancel_current":
                    self._socket.send_pyobj(self.cancel_current_experiment())
                elif command == "cancel_all":
                    self._socket.send_pyobj(self.cancel_all_experiments())
                elif command == "last_update_time":
                    self._socket.send_pyobj(self._last_update_time)
                else:
                    raise NotImplemented(f"{command} is not defined.")
            except Exception as e:
                print(e)
            time.sleep(0.01)

    def _execute_subprocess(self):
        name = self._current_experiment[0]
        path = self._current_experiment[1]
        print(f"Experiment #{self._current_rid} of {name} started")
        print(
            [
                sys.executable,
                path,
                "--rid",
                str(self._current_rid),
                "--port",
                str(self._socket_port),
            ])
        self._current_subprocess: Union[subprocess.Popen, None] = subprocess.Popen(
            [
                sys.executable,
                path,
                "--rid",
                str(self._current_rid),
                "--port",
                str(self._socket_port),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    def _experiment_worker(self):
        while True:
            if self._current_subprocess and self._current_subprocess.poll() is not None:
                print(f"Experiment #{self._current_rid} finished.")
                self._previous_experiments[self._current_rid] = self._current_experiment
                self._current_subprocess = None
                self._current_experiment = None
                self._last_update_time = time.time()
            if not self._current_subprocess:
                if self._queued_experiments:
                    self._current_rid = list(self._queued_experiments.keys())[0]
                    self._current_experiment = self._queued_experiments.pop(self._current_rid)
                    self._execute_subprocess()
                    self._last_update_time = time.time()
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

    def cancel_current_experiment(self):
        if self._current_subprocess:
            self._current_subprocess.send_signal(signal.SIGINT)
        else:
            print("There is no running experiment currently.")

    def cancel_queued_experiment(self, rid: int):
        if rid in self._queued_experiments:
            self._queued_experiments.pop(rid)
        else:
            print(f"Experiment #{rid} was already cancelled or finished.")

    def cancel_all_experiments(self):
        self._queued_experiments = {}
        if self._current_subprocess:
            self.cancel_current_experiment()


class ExperimentScheduler(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self._backend = SchedulerBackend()
        self._backend.add_experiment("test", "/home/onix/Documents/code/onix/experiments/test.py")  # test
        for kk in range(5):
            self._backend.queue_experiment("test")
        self._init_ui()
        self.update()

    def _init_ui(self):
        layout = QtWidgets.QGridLayout()
        self.queued_table = QtWidgets.QTableWidget()
        self.queued_table.setColumnCount(5)
        layout.addWidget(self.queued_table, 0, 0)
        self.selector = QtWidgets.QComboBox()
        layout.addWidget(self.selector, 0, 1)
        self.setLayout(layout)

    def update(self):
        #previous = self._backend._previous_experiments
        current = self._backend._current_experiment
        current_rid = self._backend._current_rid
        queued = self._backend._queued_experiments
        self.queued_table.clear()
        current_row = 0
        if current is not None:
            self.queued_table.insertRow(current_row)
            self.queued_table.setItem(current_row, 0, QtWidgets.QTableWidgetItem(str(current_rid)))
            self.queued_table.setItem(current_row, 1, QtWidgets.QTableWidgetItem(current[0]))
            self.queued_table.setItem(current_row, 2, QtWidgets.QTableWidgetItem(current[1]))
            self.queued_table.setItem(current_row, 3, QtWidgets.QTableWidgetItem(str(current[2])))
            self.queued_table.setItem(current_row, 4, QtWidgets.QTableWidgetItem("running"))
            current_row += 1
        for rid in queued:
            name, path, parameters = queued[rid]
            self.queued_table.insertRow(current_row)
            self.queued_table.setItem(current_row, 0, QtWidgets.QTableWidgetItem(str(rid)))
            self.queued_table.setItem(current_row, 1, QtWidgets.QTableWidgetItem(name))
            self.queued_table.setItem(current_row, 2, QtWidgets.QTableWidgetItem(path))
            self.queued_table.setItem(current_row, 3, QtWidgets.QTableWidgetItem(str(parameters)))
            self.queued_table.setItem(current_row, 4, QtWidgets.QTableWidgetItem("queued"))
            current_row += 1


if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    widget = ExperimentScheduler()
    widget.show()
    app.exec()
