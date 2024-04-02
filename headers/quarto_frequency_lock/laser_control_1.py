import os
import numpy as np
import threading
from onix.headers.quarto_frequency_lock import Quarto
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtWidgets
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt
import influxdb_client
from influxdb_client import Point
from influxdb_client.client.write_api import SYNCHRONOUS
from scipy.signal import find_peaks
from onix.headers.wavemeter.wavemeter import WM
import time

class KeyPressWindow(pg.GraphicsLayoutWidget):
    sigKeyPress = QtCore.pyqtSignal(object)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def keyPressEvent(self, ev):
        self.scene().keyPressEvent(ev)
        self.sigKeyPress.emit(ev)

wm = WM()
app = pg.mkQApp("Laser control")
q = Quarto("/dev/ttyACM1")
device_lock = threading.Lock()

win = KeyPressWindow(show=True, title="")
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

data_transmission = []
data_cavity_error = []

plots = True
def update_all():
    global rms_err
    global data_transmission
    global data_cavity_error
    if plots == True:
        with device_lock:
            data = q.get_all_data()

        data_transmission = data["transmission"]
        data_cavity_error = data["cavity_error"]

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
win.addItem(lock_state_proxy, row = 5, col = 0, colspan = 1)

## Output Offset Spinbox
def _offset():
    with device_lock:
        q.set_output_offset(offset.value())

with device_lock:
    initial_offset = q.get_output_offset()

offset = QtWidgets.QDoubleSpinBox(prefix = "Offset: ", suffix = " V")
offset.setValue(initial_offset)
offset.setDecimals(3)
offset.setSingleStep(0.001)
offset.valueChanged.connect(_offset)
offset.setMinimum(0)
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
scan.setDecimals(3)
scan.setSingleStep(0.001)
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
        stop_plots.setStyleSheet("background-color: red; color: white")
    else:
        plots = True
        stop_plots.setText("Plots On")
        stop_plots.setStyleSheet("background-color: green; color: white")

stop_plots = QtWidgets.QPushButton("Plots On")
stop_plots.setStyleSheet("background-color: green; color: white")
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
    last_transmission.setText(f"Transmission: {round_sig(val,3)} V")

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
    if plots == True:
        with device_lock:
            err_data = q.get_all_data()["cavity_error"]
        err_squared = np.power(err_data, 2)
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

rms_err_timer = QtCore.QTimer()
rms_err_timer.timeout.connect(update_rms_err)
rms_err_timer.start(250)

## Monitor the integral and output using influx db
token = os.environ.get("INFLUXDB_TOKEN")
org = "onix"
url = "http://onix-pc:8086"
bucket_week = "week"

write_client = influxdb_client.InfluxDBClient(url=url, token=token, org=org)
write_api = write_client.write_api(write_options=SYNCHRONOUS)


if q.get_state() == 0:
    counter_starts_off = True
else:
    counter_starts_off = False

unlock_counter = 0


def record_data():
    try:
        point = Point("laser_controller")
        with device_lock:
            integral = q.get_integral()
            output = q.get_last_output_point()
            dc_offset = q.get_dc_offset()
            unlock_counter = q.get_unlock_counter()

        point.field("integral", integral)
        point.field("output", output)
        point.field("dc offset", dc_offset)
        point.field("unlock counter", unlock_counter)
        write_api.write(bucket=bucket_week, org="onix", record=point)
    except:
        print("Error recording to InfluxDB")

influx_db_timer = QtCore.QTimer()
influx_db_timer.timeout.connect(record_data)
influx_db_timer.start(5000) #5 seconds





























## Keyboard testing

def keyPressed(evt):
    print(evt.key())

    if q.get_state() == 0:
        # print("Key pressed")
        

        if evt.key() == Qt.Key_Left:
            print("test1") # left
            offset.setValue(offset.value() + 0.01)


        if evt.key() == Qt.Key_Up:
            print("test2") # up
            if q.get_dc_offset() < 10:
                q.set_dc_offset(q.get_dc_offset() + 0.1)
                print(f"cavity error = {np.average(data_cavity_error)}")
                print(f"DC offset = {q.get_dc_offset()}")


        if evt.key() == Qt.Key_Right:
            print("test3") # right
            offset.setValue(offset.value() - 0.01)


        if evt.key() == Qt.Key_Down:
            print("test4") # down
            if q.get_dc_offset() > -10:
                q.set_dc_offset(q.get_dc_offset() - 0.1)
                print(f"cavity error = {np.average(data_cavity_error)}")
                print(f"DC offset = {q.get_dc_offset()}")


    # if evt.key() == Qt.Key_Control: # ctrl
    #     if lock_state.text() == "Lock On" or lock_state.text() == "Autorelock On":
    #         lock_state.setText("Lock Off")
    #         lock_state.setStyleSheet("background-color: Red; color: white;")
    #         with device_lock:
    #             q.set_state(0)
    #     elif lock_state.text() == "Lock Off":
    #         lock_state.setText("Autorelock On")
    #         lock_state.setStyleSheet("background-color: green; color: white;")
    #         with device_lock:
    #             q.set_state(2)
        
win.sigKeyPress.connect(keyPressed)



## Lock On / Off Button
def on_button_pressed_2():
    global initial_super_relock_state
    if super_relock_state.text() == "EXTREME Autorelock On":
        initial_super_relock_state = 0
        super_relock_state.setText("EXTREME Autorelock Off")
        super_relock_state.setStyleSheet("background-color: Red; color: white;")
    elif super_relock_state.text() == "EXTREME Autorelock Off":
        initial_super_relock_state = 1
        super_relock_state.setText("EXTREME Autorelock On")
        super_relock_state.setStyleSheet("background-color: green; color: white;")

initial_super_relock_state = 0

super_relock_state = QtWidgets.QPushButton()
if initial_super_relock_state == 1:
    super_relock_state.setText("EXTREME Autorelock On")
    super_relock_state.setStyleSheet("background-color: green; color: white;")
elif initial_super_relock_state == 0:
    super_relock_state.setText("EXTREME Autorelock Off")
    super_relock_state.setStyleSheet("background-color: Red; color: white;")

super_relock_state.clicked.connect(on_button_pressed_2)
super_relock_state_proxy = QtWidgets.QGraphicsProxyWidget()
super_relock_state_proxy.setWidget(super_relock_state)
win.addItem(super_relock_state_proxy, row = 5, col = 1, colspan = 1)

# def lock_param_update():
#     if initial_super_relock_state == 1:
#         freq = wm.read_frequency(5) - 516847 # MHz
#         print(freq)
#         if 100 > freq > -100:
#             peak_xs, peak_ys = find_peaks(data_transmission, height = 0.003)
#             l_peak_xs, l_peak_ys = find_peaks(data_transmission, heights= 0.1)
#             peak_ys = peak_ys["peak_heights"]
#             if len(peak_xs) == 3:
#                 if peak_xs[1] < 475:
#                     offset.setValue(offset.value() - 0.001)
#                 elif peak_xs[1] > 525:
#                     offset.setValue(offset.value() + 0.001)
#                 else:
#                     if scan.value() > 0.1:
#                         scan.setValue(scan.value() - 0.01)
#             elif len(peak_xs) < 3:
#                 scan.setValue(scan.value() + 0.1)
#             else:
#                 ll = np.argmax(peak_ys)
#                 scan.setValue(scan.value() - 0.01)
#                 if peak_xs[ll] < 475:
#                     offset.setValue(offset.value() - 0.01)
#                 elif peak_xs[ll] > 525:
#                     offset.setValue(offset.value() + 0.01)
#                 else:
#                     if scan.value() > 0.1:
#                         scan.setValue(scan.value() - 0.01)
                
#             print(peak_xs)
#             # print(peak_xs[1])
#         else:
#             pass # wrong frequency

#     else:
#         pass
q.set_dc_offset(0)
offset_scan_direction = 0
unhop_val = True
def lock_param_update():
    global offset_scan_direction
    if q.get_state() == 0:
        if initial_super_relock_state == 1:
            avg_data_cavity_error = np.average(data_cavity_error)
            dc_offset = q.get_dc_offset()
            if np.abs(avg_data_cavity_error) > 0.01:
                if avg_data_cavity_error < 0 and dc_offset < 10:
                    q.set_dc_offset(dc_offset + 0.1)
                if avg_data_cavity_error > 0 and dc_offset > -10:
                    q.set_dc_offset(dc_offset - 0.1)
            else:
                wm_freq = wm.read_frequency(5)
                wm_freq_diff = wm_freq - 516847.58

                if abs(wm_freq_diff) < 10:
                    if abs(wm_freq_diff) > 0.1:
                        scan.setValue(0.5)

                        step_size = max(0.2, abs(0.2*wm_freq_diff))
                        if scan.value() > 1:
                            scan.setValue(scan.value() + 0.1)
                        if offset_scan_direction == 0:
                            offset.setValue(offset.value() + step_size)
                        elif offset_scan_direction == 1:
                            offset.setValue(offset.value() - step_size)


                        if wm_freq_diff > 0:
                            offset_scan_direction = 1
                        else:
                            offset_scan_direction = 0
                    else:
                        peak_xs, peak_ys = find_peaks(data_transmission, height = 0.005)
                        peak_ys = peak_ys["peak_heights"]
                        # print(l_peak_xs)
                        if len(peak_xs) > 0:
                            peak_x = peak_xs[np.argmax(peak_ys)]
                            if peak_x < 475:
                                offset.setValue(offset.value() - 0.007)
                            elif peak_x > 525:
                                offset.setValue(offset.value() + 0.007)
                            elif scan.value() > 0.1:
                                step_size = max(scan.value()** 3, 0.05)
                                scan.setValue(max(scan.value() - step_size, 0.1))
                            else:
                                lock_state.setText("Autorelock On")
                                lock_state.setStyleSheet("background-color: green; color: white;")
                                with device_lock:
                                    q.set_state(2)
                        else:
                            scan.setValue(0.5)
                                

                else: 
                    pass
                    # global unhop_val
                    # if scan.value() != 0.1:
                    #     scan.setValue(0.1)
                    # if unhop_val == True:
                    #     offset.setValue(0)
                    #     unhop_val = False
                    # else:
                    #     offset.setValue(10)
                    #     unhop_val = True


lock_param_update_timer = QtCore.QTimer()
lock_param_update_timer.timeout.connect(lock_param_update)
lock_param_update_timer.start(50)

# check transmission

def transmission_check():
    global initial_super_relock_state
    if q.get_state() == 2 and initial_super_relock_state == 1:
        if np.average(data_transmission) < 0.1:
            # unlocked        
            lock_state.setText("Lock Off")
            lock_state.setStyleSheet("background-color: Red; color: white;")
            with device_lock:
                q.set_state(0)


transmission_check_timer = QtCore.QTimer()
transmission_check_timer.timeout.connect(transmission_check)
transmission_check_timer.start(100)

wavemeter_text_label = pg.LabelItem(f"Wavemeter: ")
win.addItem(wavemeter_text_label, row = 4,  col = 0, colspan = 1)

dc_offset_text_label = pg.LabelItem(f"DC Offset: ")
win.addItem(dc_offset_text_label, row = 4,  col = 1, colspan = 1)

mode_hop_text_label = pg.LabelItem(f"")
win.addItem(mode_hop_text_label, row = 4,  col = 3, colspan = 1)

def update_text():
    global wavemeter_text_label
    wm_freq = wm.read_frequency(5)
    if type(wm_freq) == str:
        wavemeter_text_label.setText(wm_freq)
    else:
        wm_freq_diff = wm_freq - 516847.58
        if abs(wm_freq_diff) > 0.1:
            color = "#E61414"
        else:
            color = "#33FF33"
        wavemeter_text_label.setText(f"Wavemeter: {wm_freq:.4f} MHz", color = color)

    dc_offset_text_label.setText(f"DC Offset: {q.get_dc_offset():.4f}", color = "#FFFFFF")

    if abs(wm_freq_diff) > 50:
        mode_hop_text_label.setText("MODE HOPPED", color="#FF0000")
    else:
        mode_hop_text_label.setText("", color="#FF0000")





update_wavemeter_frequency_timer = QtCore.QTimer()
update_wavemeter_frequency_timer.timeout.connect(update_text)
update_wavemeter_frequency_timer.start(50)


if __name__ == '__main__':
    pg.exec()