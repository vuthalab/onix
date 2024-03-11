from onix.headers.quarto_intensity_lock import Quarto
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtWidgets
import threading
from PyQt5.QtWidgets import *
import numpy as np
from onix.analysis.power_spectrum import CCedPowerSpectrum

def round_sig(x, sig=3):
    """
    Rounds to specified number of significant figures
    """
    return round(x, sig-int(np.floor(np.log10(abs(x))))-1)

app = pg.mkQApp("Intensity control")
q = Quarto("/dev/ttyACM5")
device_lock = threading.Lock()

DEFAULT_GET_DATA_LENGTH = 30000

## Plots
win = pg.GraphicsLayoutWidget(show=True, title="")
win.resize(1000,600)
pg.setConfigOptions(antialias=True)

primary_bg_pen = pg.mkPen(color = 'y', style=QtCore.Qt.DotLine) # set background lines to be dotted
monitor_bg_pen = pg.mkPen(color = 'r', style=QtCore.Qt.DotLine)

noise = CCedPowerSpectrum(DEFAULT_GET_DATA_LENGTH, q.sample_time, max_points_per_decade=200)

relative_voltage_spectrum = win.addPlot(title="Relative Voltage Spectrum", colspan = 7)
relative_voltage_spectrum.setMouseEnabled(x=False)
relative_voltage_spectrum.setLogMode(x = True,y = True)
relative_voltage_spectrum.addLegend(offset = (50,0))
relative_voltage_spectrum.setLabel("left", text = "Relative power noise density Hz<sup>-1</sup>")
relative_voltage_spectrum.setLabel("bottom", text = "Frequency [Hz]")

primary_signal = relative_voltage_spectrum.plot(pen='y', name = "Primary")
primary_bg = relative_voltage_spectrum.plot(pen=primary_bg_pen, name = "Primary Background", )

monitor_signal = relative_voltage_spectrum.plot(pen='r', name = "Monitor")
monitor_bg = relative_voltage_spectrum.plot(pen=monitor_bg_pen, name = "Monitor Background", alpha = 0.01)

cc = relative_voltage_spectrum.plot(pen='g', name = "Cross Correlated")

plots = True
frame = 0
averages = 1

def update_relative_voltage_spectrum():
    global frame
    if plots == True:
        with device_lock:
            primary_data, monitor_data = q.get_both_pd_data()
        if frame < averages:  
            noise.add_data(primary_data, monitor_data)
        else:
            noise.update_data(primary_data, monitor_data)
    
        primary_spectrum = noise.signal_1_relative_voltage_spectrum
        primary_signal.setData(noise.f, primary_spectrum)

        monitor_spectrum = noise.signal_2_relative_voltage_spectrum
        monitor_signal.setData(noise.f, monitor_spectrum)

        cc_spectrum = noise.cc_relative_voltage_spectrum
        cc.setData(noise.f, np.real(cc_spectrum)) 

        primary_background = np.ones(len(noise.f)) * 1e-7 / noise.error_signal_1_average 
        monitor_background = np.ones(len(noise.f)) * 1e-7 / noise.error_signal_2_average
        primary_bg.setData(noise.f, primary_background) 
        monitor_bg.setData(noise.f, monitor_background)  

        relative_voltage_spectrum.legend.removeItem(primary_signal)
        relative_voltage_spectrum.legend.addItem(primary_signal, f"Primary: {round_sig(noise.error_signal_1_average, 3)} V")

        relative_voltage_spectrum.legend.removeItem(monitor_signal)
        relative_voltage_spectrum.legend.addItem(monitor_signal, f"Monitor: {round_sig(noise.error_signal_2_average, 3)} V")
        try:
            frame += 1 
        except:
            frame = averages
    else:
        pass
win.nextRow()

timer = QtCore.QTimer()
timer.timeout.connect(update_relative_voltage_spectrum)
timer.start(100)

## Lock On / Off Button
def on_button_pressed():
    if lock_state.text() == "Lock On":
        lock_state.setText("Lock Off")
        lock_state.setStyleSheet("background-color: Red; color: white;")
        with device_lock:
            q.set_pid_state(0)
    elif lock_state.text() == "Lock Off":
        lock_state.setText("Lock On")
        lock_state.setStyleSheet("background-color: green; color: white;")
        with device_lock:
            q.set_pid_state(1)

with device_lock:
    initial_lock_state = q.get_pid_state()
lock_state = QtWidgets.QPushButton()
if initial_lock_state == 1:
    lock_state.setText("Lock On")
    lock_state.setStyleSheet("background-color: green; color: white;")
elif initial_lock_state == 0:
    lock_state.setText("Lock Off")
    lock_state.setStyleSheet("background-color: Red; color: white;")

lock_state.clicked.connect(on_button_pressed)
lock_state_proxy = QtWidgets.QGraphicsProxyWidget()
lock_state_proxy.setWidget(lock_state)
win.addItem(lock_state_proxy, row = 2, col = 0)

## P Gain Spinbox
def _set_p():
    with device_lock:
        q.set_p_gain(p_gain.value())

with device_lock:
    initial_p = q.get_p_gain()
   
p_gain = QtWidgets.QDoubleSpinBox(prefix = "P: ")
p_gain.setMinimum(-1e6)
p_gain.setMaximum(1e6)
p_gain.setValue(initial_p)
p_gain.setDecimals(4)
p_gain.setSingleStep(0.001)
p_gain.editingFinished.connect(_set_p)
p_gain_proxy = QtWidgets.QGraphicsProxyWidget()
p_gain_proxy.setWidget(p_gain)
win.addItem(p_gain_proxy, row = 2, col = 1)

## I Time Spinbox
def _set_i():
    with device_lock:
        q.set_i_time(i_time.value())

with device_lock:
    initial_i = q.get_i_time()
   
i_time = QtWidgets.QDoubleSpinBox(prefix = "I: ", suffix = "us")
i_time.setMinimum(0)
i_time.setMaximum(1e6)
i_time.setValue(initial_i)
i_time.setDecimals(1)
i_time.setSingleStep(1)
i_time.editingFinished.connect(_set_i)
i_time_proxy = QtWidgets.QGraphicsProxyWidget()
i_time_proxy.setWidget(i_time)
win.addItem(i_time_proxy, row = 2, col = 2)

## Set D Time Spinbox
def _set_d():
    with device_lock:
        q.set_d_time(d_time.value())

with device_lock:
    initial_d = q.get_d_time()

d_time = QtWidgets.QDoubleSpinBox(prefix = "D: ", suffix = " us")
d_time.setMinimum(0)
d_time.setMaximum(1e6)
d_time.setValue(initial_d)
d_time.setDecimals(1)
d_time.setSingleStep(1)
d_time.editingFinished.connect(_set_d)
d_time_proxy = QtWidgets.QGraphicsProxyWidget()
d_time_proxy.setWidget(d_time)
win.addItem(d_time_proxy, row = 2, col = 3)

# PID Setpoint Spinbox
def _set_setpoint():
    with device_lock:
        q.set_setpoint(set_setpoint.value())

with device_lock:
    initial_setpoint = q.get_setpoint()

set_setpoint = QtWidgets.QDoubleSpinBox(prefix = "Setpoint: ", suffix = " V")
set_setpoint.setValue(initial_setpoint)
set_setpoint.setDecimals(2)
set_setpoint.setMinimum(0)
set_setpoint.setMaximum(10)
set_setpoint.setSingleStep(0.01)
set_setpoint.editingFinished.connect(_set_setpoint)
set_sample_time_proxy = QtWidgets.QGraphicsProxyWidget()
set_sample_time_proxy.setWidget(set_setpoint)
win.addItem(set_sample_time_proxy, row = 2, col = 4)

## Change FFT Averages Spinbox
def _change_averages():
    global averages
    global frame
    global noise
    averages = averages_button.value()
    frame = 0
    noise = CCedPowerSpectrum(DEFAULT_GET_DATA_LENGTH, q.sample_time, max_points_per_decade=200)

averages_button = QtWidgets.QSpinBox(prefix = "Averages: ")
averages_button.setValue(averages)
averages_button.valueChanged.connect(_change_averages)
averages_button_proxy = QtWidgets.QGraphicsProxyWidget()
averages_button_proxy.setWidget(averages_button)
win.addItem(averages_button_proxy, row = 2, col = 5)

## Plots On / Off Button
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
win.addItem(stop_plots_proxy, row = 2, col = 6)

if __name__ == '__main__':
    pg.exec()
