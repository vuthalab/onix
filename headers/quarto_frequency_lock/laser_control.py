import os
import numpy as np
import threading
from onix.headers.quarto_frequency_lock import Quarto
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtWidgets
from PyQt5.QtWidgets import *
import influxdb_client
from influxdb_client import Point
from influxdb_client.client.write_api import SYNCHRONOUS

app = pg.mkQApp("Laser control")
q = Quarto("/dev/ttyACM3")
device_lock = threading.Lock()

win = pg.GraphicsLayoutWidget(show=True, title="")
win.resize(1000,600)
pg.setConfigOptions(antialias=True)

LENGTH = 1000

p_error = win.addPlot(title="error signal", colspan = 4)
p_error.setMouseEnabled(x=False)
error = p_error.plot(pen='y')
def update_p_error(data):
    global error
    error.setData(data)
win.nextRow()

p_output = win.addPlot(title="output signal", colspan = 4)
p_output.setMouseEnabled(x=False)
output = p_output.plot(pen='y')
def update_p_output(data):
    global output
    output.setData(data)
win.nextRow()

p_transmission = win.addPlot(title="transmission signal", colspan = 4)
p_transmission.setMouseEnabled(x=False)
transmission = p_transmission.plot(pen='y')
def update_p_transmission(data):
    global transmission
    transmission.setData(data)
win.nextRow()

p_cavity_error = win.addPlot(title="cavity error signal", colspan = 4)
p_cavity_error.setMouseEnabled(x=False)
cavity_error = p_cavity_error.plot(pen='y')
def update_p_cavity_error(data):
    global cavity_error
    cavity_error.setData(data)
win.nextRow()

plots = True
def update_all():
    global rms_err
    if plots == True:
        with device_lock:
            data = q.get_all_data()
        update_p_error(data["error"])
        update_p_output(data["output"])
        update_p_transmission(data["transmission"])
        update_p_cavity_error(data["cavity_error"])
    else:
        pass

timer = QtCore.QTimer()
timer.timeout.connect(update_all)
timer.start(50)

## Lock On / Off Button
def on_button_pressed():
    if lock_state.text() == "Lock On" or lock_state.text() == "Autorelock On":
        lock_state.setText("Lock Off")
        lock_state.setStyleSheet("background-color: Red; color: white;")
        with device_lock:
            q.set_state(0)
    elif lock_state.text() == "Lock Off":
        lock_state.setText("Autorelock On")
        lock_state.setStyleSheet("background-color: green; color: white;")
        with device_lock:
            q.set_state(2)

with device_lock:
    initial_lock_state = q.get_state()
lock_state = QtWidgets.QPushButton()
if initial_lock_state == 1:
    lock_state.setText("Lock On")
    lock_state.setStyleSheet("background-color: green; color: white;")
elif initial_lock_state == 0:
    lock_state.setText("Lock Off")
    lock_state.setStyleSheet("background-color: Red; color: white;")
elif initial_lock_state == 2:
    lock_state.setText("Autorelock On")
    lock_state.setStyleSheet("background-color: green; color: white;")

lock_state.clicked.connect(on_button_pressed)
lock_state_proxy = QtWidgets.QGraphicsProxyWidget()
lock_state_proxy.setWidget(lock_state)
win.addItem(lock_state_proxy, row = 5, col = 0, colspan = 2)

## Output Offset Spinbox
def _offset():
    with device_lock:
        q.set_output_offset(offset.value())

with device_lock:
    initial_offset = q.get_output_offset()
offset = QtWidgets.QDoubleSpinBox(prefix = "Offset: ", suffix = " V")
offset.setValue(initial_offset)
offset.setDecimals(2)
offset.setSingleStep(0.01)
offset.valueChanged.connect(_offset)
offset.setMinimum(-10)
offset.setMaximum(10)
offset_proxy = QtWidgets.QGraphicsProxyWidget()
offset_proxy.setWidget(offset)
win.addItem(offset_proxy, row = 5, col = 2)

## Scan Spinbox
def _scan():
    with device_lock:
        q.set_scan(scan.value())

scan = QtWidgets.QDoubleSpinBox(prefix = "Scan: ", suffix = " V")
with device_lock:
    initial_scan = q.get_scan()
scan.setValue(initial_scan)
scan.setDecimals(2)
scan.setSingleStep(0.01)
scan.valueChanged.connect(_scan)
scan.setMinimum(0)
scan.setMaximum(10)
scan_proxy = QtWidgets.QGraphicsProxyWidget()
scan_proxy.setWidget(scan)
win.addItem(scan_proxy, row = 5, col = 3)
win.nextRow()

## Integral and Output Warnings
def update_warning():
    with device_lock:
        state = q.get_state()
    if state == 0:
        warning.setStyleSheet("background-color: white; color: black")
        warning_text = "No Warnings"
    else:
        integral_warning, output_warning = q.output_limit_indicator()
        warning_text = integral_warning + " " + output_warning
        if "out" in integral_warning or "out" in output_warning:
            warning.setStyleSheet("background-color: red; color: white")
        elif "warning" in integral_warning or "warning" in output_warning:
            warning.setStyleSheet("background-color: yellow; color: black")
        else:
            warning.setStyleSheet("background-color: green; color: white")
    warning.setText(warning_text)

warning = QtWidgets.QPushButton()
warning_proxy = QtWidgets.QGraphicsProxyWidget()
warning_proxy.setWidget(warning)
update_warning()
win.addItem(warning_proxy, row = 6, col = 0)

warning_timer = QtCore.QTimer()
warning_timer.timeout.connect(update_warning)
warning_timer.start(5000)

## Stop Plots Button
def stop_plots_pressed():
    global plots
    if plots == True:
        plots = False
        stop_plots.setText("Plots Off")
    else:
        plots = True
        stop_plots.setText("Plots On")

stop_plots = QtWidgets.QPushButton("Plots On")
stop_plots.clicked.connect(stop_plots_pressed)
stop_plots_proxy = QtWidgets.QGraphicsProxyWidget()
stop_plots_proxy.setWidget(stop_plots)
win.addItem(stop_plots_proxy, row = 6, col = 1)

## Transmission
def round_sig(x, sig=3):
    """
    Rounds to specified number of significant figures
    """
    return round(x, sig-int(np.floor(np.log10(abs(x))))-1)

def update_transmission():
    with device_lock:
        val = q.get_last_transmission_point()
    last_transmission.setText(f"Transmission: {round_sig(val,3)}")

last_transmission = QtWidgets.QPushButton()
last_transmission_proxy = QtWidgets.QGraphicsProxyWidget()
last_transmission_proxy.setWidget(last_transmission)
update_transmission()
win.addItem(last_transmission_proxy, row = 6, col = 2)

last_transmission_timer = QtCore.QTimer()
last_transmission_timer.timeout.connect(update_transmission)
last_transmission_timer.start(1000)

## RMS Error
track_rms_err = True

def _toggle_rms_error():
    global track_rms_err
    if rms_err.text == "RMS Error: --":
        track_rms_err = True
    else: 
        track_rms_err = False
        rms_err.setText("RMS Error: --")

def update_rms_err():
    if track_rms_err == True:
        with device_lock:
            err_data = q.get_all_data()["cavity_error"]
        err_squared = np.power(err_data, 2)
        print(err_squared)
        value = np.sqrt(sum(err_squared) / len(err_squared))
        rms_err.setText(f"RMS Error: {round_sig(value,3)} V")
    else: 
        pass

rms_err = QtWidgets.QPushButton()
rms_err_proxy = QtWidgets.QGraphicsProxyWidget()
rms_err_proxy.setWidget(rms_err)
stop_plots.clicked.connect(_toggle_rms_error)
update_rms_err()
win.addItem(rms_err_proxy, row = 6, col = 3)

## Monitor the integral and output using influx db
token = os.environ.get("INFLUXDB_TOKEN")
org = "onix"
url = "http://onix-pc:8086"
bucket_week = "week"

write_client = influxdb_client.InfluxDBClient(url=url, token=token, org=org)
write_api = write_client.write_api(write_options=SYNCHRONOUS)

def record_data():
    try:
        point = Point("laser_controller")
        with device_lock:
            integral = q.get_integral()
            output = q.get_last_output_point()
        point.field("integral", integral)
        point.field("output", output)
        write_api.write(bucket=bucket_week, org="onix", record=point)
    except:
        print("Error recording integral and output to InfluxDB")

influx_db_timer = QtCore.QTimer()
influx_db_timer.timeout.connect(record_data)
influx_db_timer.start(5000) #5 seconds

if __name__ == '__main__':
    pg.exec()
