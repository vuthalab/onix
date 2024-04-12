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
        self._experiments_last_update_time = time.time()
        self._queue_last_update_time = time.time()
        
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
                elif command == "list_experiments":
                    self._socket.send_pyobj(self._experiments)
                elif command == "list_queue":
                    self._socket.send_pyobj(self._queued_experiments)
                elif command == "list_previous":
                    self._socket.send_pyobj(self._previous_experiments)
                elif command == "get_current":
                    self._socket.send_pyobj((self._current_rid, self._current_experiment))
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
                elif command == "add_experiment":
                    name, path = data
                    self._socket.send_pyobj(self.add_experiment(name, path))
                elif command == "remove_experiment":
                    name = data
                    self._socket.send_pyobj(self.remove_experiment(name))
                elif command == "queue_last_update_time":
                    self._socket.send_pyobj(self._queue_last_update_time)
                elif command == "experiments_last_update_time":
                    self._socket.send_pyobj(self._experiments_last_update_time)
                else:
                    raise NotImplemented(f"{command} is not defined.")
            except Exception as e:
                print(e)
            time.sleep(0.01)

    def _execute_subprocess(self):
        name = self._current_experiment[0]
        path = self._current_experiment[1]
        print(f"Experiment #{self._current_rid} of {name} started")
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
                self._queue_last_update_time = time.time()
            if not self._current_subprocess:
                if self._queued_experiments:
                    self._current_rid = list(self._queued_experiments.keys())[0]
                    self._current_experiment = self._queued_experiments.pop(self._current_rid)
                    self._execute_subprocess()
                    self._queue_last_update_time = time.time()
            time.sleep(0.01)

    def add_experiment(self, name: str, path: str):
        self._experiments[name] = path
        self._experiments_last_update_time = time.time()

    def remove_experiment(self, name: str):
        self._experiments_last_update_time = time.time()
        return self._experiments.pop(name, None)

    def queue_experiment(self, name: str, overriden_parameters: dict[str, Any] = None):
        if name not in self._experiments:
            print(f"Experiment {name} is not defined.")
            return None
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
        self._queue_last_update_time = time.time()
        return rid

    def cancel_current_experiment(self):
        if self._current_subprocess:
            self._current_subprocess.send_signal(signal.SIGINT)
        else:
            print("There is no running experiment currently.")
        self._queue_last_update_time = time.time()

    def cancel_queued_experiment(self, rid: int):
        if rid in self._queued_experiments:
            self._queued_experiments.pop(rid)
        else:
            print(f"Experiment #{rid} was already cancelled or finished.")
        self._queue_last_update_time = time.time()

    def cancel_all_experiments(self):
        self._queued_experiments = {}
        if self._current_subprocess:
            self.cancel_current_experiment()
        self._queue_last_update_time = time.time()


class SchedulerClient:
    def __init__(self, ip: str = "localhost", port: int = PORT):
        self._queue_last_updated_time = None
        self._experiments_last_updated_time = None

        self.current_experiment = ()
        self.queued_experiments = {}
        self.experiments = {}

        context = zmq.Context()
        self._socket = context.socket(zmq.REQ)
        self._socket.connect(f"tcp://{ip}:{port}")

    def close(self):
        self._socket.close()

    def _send_command(self, command: str, data: Any = None) -> Any:
        self._socket.send_pyobj((command, data))
        return self._socket.recv_pyobj()

    def get_parameters(self, rid: int) -> Union[dict, None]:
        return self._send_command("parameters", rid)

    def queue_experiment(self, name: str, overriden_parameters: Union[dict, None] = None):
        return self._send_command("queue", (name, overriden_parameters))

    def cancel_experiment(self, rid: int):
        return self._send_command("cancel", rid)

    def cancel_current_experiment(self):
        return self._send_command("cancel_current")

    def cancel_all_experiments(self):
        return self._send_command("cancel_all")

    def add_experiment(self, name: str, path: str):
        return self._send_command("add_experiment", (name, path))

    def remove_experiment(self, name: str):
        return self._send_command("remove_experiment", name)

    def _list_experiments(self) -> dict:
        return self._send_command("list_experiments")

    def _get_current_experiment(self) -> dict:
        return self._send_command("get_current")

    def _list_queued_experiments(self) -> dict:
        return self._send_command("list_queue")

    def _list_previous_experiments(self) -> dict:
        return self._send_command("list_previous")

    def _is_queue_up_to_date(self) -> bool:
        updated_time = self._send_command("queue_last_update_time")
        if updated_time != self._queue_last_updated_time:
            self._queue_last_updated_time = updated_time
            return False
        return True

    def _is_experiments_up_to_date(self) -> bool:
        updated_time = self._send_command("experiments_last_update_time")
        if updated_time != self._experiments_last_updated_time:
            self._experiments_last_updated_time = updated_time
            return False
        return True

    def update_queue(self) -> bool:
        if self._is_queue_up_to_date():
            return True
        else:
            self.queued_experiments = self._list_queued_experiments()
            self.current_experiment = self._get_current_experiment()
            return False

    def update_experiments(self) -> bool:
        if self._is_experiments_up_to_date():
            return True
        else:
            self.experiments = self._list_experiments()
            return False


class SchedulerGUI(QtWidgets.QWidget):
    signal_update_queue = QtCore.pyqtSignal()
    signal_update_experiments = QtCore.pyqtSignal()

    def __init__(self, ip: str = "localhost", port: int = PORT):
        super().__init__()
        self._client = SchedulerClient(ip, port)
        self._init_ui()

        self.signal_update_queue.connect(self._on_update_queue)
        self.signal_update_experiments.connect(self._on_update_experiments)

        self._update_thread = threading.Thread(target=self._update_worker, daemon=True)
        self._update_thread.start()

    def _init_ui(self):
        layout = QtWidgets.QGridLayout()
        self.queued_table = QtWidgets.QTableWidget()
        self.queued_table.setColumnCount(5)
        self.queued_table.setHorizontalHeaderLabels(["ID", "Name", "Path", "Parameters", "Status"])
        layout.addWidget(self.queued_table, 0, 0, 2, 1)
        self.selector = QtWidgets.QComboBox()
        layout.addWidget(self.selector, 0, 1)
        self.schedule = QtWidgets.QPushButton("Schedule")
        self.schedule.setCheckable(False)
        self.schedule.clicked.connect(self._on_schedule_pushed)
        layout.addWidget(self.schedule, 1, 1)
        self.setLayout(layout)

    def _add_queue(self, rid: int, name: str, path: str, parameters: dict, status: str):
        last_row = self.queued_table.rowCount()
        self.queued_table.insertRow(last_row)
        self.queued_table.setItem(last_row, 0, QtWidgets.QTableWidgetItem(str(rid)))
        self.queued_table.setItem(last_row, 1, QtWidgets.QTableWidgetItem(name))
        self.queued_table.setItem(last_row, 2, QtWidgets.QTableWidgetItem(path))
        self.queued_table.setItem(last_row, 3, QtWidgets.QTableWidgetItem(str(parameters["overriden"])))
        self.queued_table.setItem(last_row, 4, QtWidgets.QTableWidgetItem(status))

    @QtCore.pyqtSlot()
    def _on_update_queue(self):
        #self.queued_table.clear()
        while self.queued_table.rowCount() > 0:
            self.queued_table.removeRow(0)
        if self._client.current_experiment[1] is not None:
            self._add_queue(
                rid=self._client.current_experiment[0],
                name=self._client.current_experiment[1][0],
                path=self._client.current_experiment[1][1],
                parameters=self._client.current_experiment[1][2],
                status="running",
            )
        for rid in self._client.queued_experiments:
            self._add_queue(
                rid=rid,
                name=self._client.queued_experiments[rid][0],
                path=self._client.queued_experiments[rid][1],
                parameters=self._client.queued_experiments[rid][2],
                status="queued",
            )

    @QtCore.pyqtSlot()
    def _on_update_experiments(self):
        self.selector.clear()
        for name in self._client.experiments:
            self.selector.addItem(name, self._client.experiments[name])

    def _on_schedule_pushed(self, state):
        if self.selector.currentIndex() >= 0:
            name = self.selector.itemData(self.selector.currentIndex())
            self._client.queue_experiment(name)
        else:
            print("No experiment selected.")

    def _update_worker(self):
        while True:
            self._update_experiments()
            self._update_queue()
            time.sleep(0.25)

    def _update_queue(self):
        if not self._client.update_queue():
            print("B")
            self.signal_update_queue.emit()

    def _update_experiments(self):
        if not self._client.update_experiments():
            self.signal_update_experiments.emit()


if __name__ == "__main__":
    run_gui = False
    if len(sys.argv) > 1:
        if sys.argv[1] == "--gui":
            run_gui = True
    if run_gui:
        app = QtWidgets.QApplication([])
        widget = SchedulerGUI()
        widget.show()
        app.exec()
    else:
        backend = SchedulerBackend()
        backend.add_experiment("test", "/home/onix/Documents/code/onix/experiments/test.py")  # test
        for kk in range(5):
            backend.queue_experiment("test")
        try:
            while True:
                time.sleep(0.01)
        except KeyboardInterrupt:
            pass
