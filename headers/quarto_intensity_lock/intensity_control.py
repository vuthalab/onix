from onix.headers.quarto_intensity_lock import Quarto
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtWidgets
import threading
from PyQt5.QtWidgets import *
import numpy as np
from onix.analysis.power_spectrum import CCedPowerSpectrum
#import sys
#import random
app = pg.mkQApp("Intensity control")
q = Quarto("/dev/ttyACM5")

device_lock = threading.Lock()

win = pg.GraphicsLayoutWidget(show=True, title="")
win.resize(1000,600)
pg.setConfigOptions(antialias=True)

DEFAULT_GET_DATA_LENGTH = 30000

noise = CCedPowerSpectrum(DEFAULT_GET_DATA_LENGTH, q.sample_time, max_points_per_decade=200)
#noise = CCedPowerSpectrum(DEFAULT_GET_DATA_LENGTH, 2e-6, max_points_per_decade=200)
relative_voltage_spectrum = win.addPlot(title="Relative Voltage Spectrum", colspan = 7)
relative_voltage_spectrum.setMouseEnabled(x=False)
relative_voltage_spectrum.setLogMode(x = True,y = True)
relative_voltage_spectrum.addLegend(offset = (50,0))
relative_voltage_spectrum.setLabel("left", text = "Relative power noise density Hz<sup>-1</sup>")
relative_voltage_spectrum.setLabel("bottom", text = "Frequency [Hz]")
primary_signal = relative_voltage_spectrum.plot(pen='y', name = "Primary")
primary_bg = relative_voltage_spectrum.plot(pen='w', name = "Primary Background")
monitor_signal = relative_voltage_spectrum.plot(pen='r', name = "Monitor")
monitor_bg = relative_voltage_spectrum.plot(pen='w', name = "Monitor Background")
cc = relative_voltage_spectrum.plot(pen='g', name = "Cross Correlated")

plots = True
frame = 0
averages = 1

def update_relative_voltage_spectrum():
    global frame
    print(frame)
    if plots == True:
        with device_lock:
            primary_data, monitor_data = q.get_both_pd_data()
            #primary_data = np.ones(30000) * random.random()
            #monitor_data = np.ones(30000) * random.random()
        if frame < averages:  # TODO: what if the averages is changed lower?
            noise.add_data(primary_data, monitor_data)
            #print("add data")
        else:
            noise.update_data(primary_data, monitor_data)
            #print("Update data")

        primary_spectrum = noise.signal_1_relative_voltage_spectrum
        primary_signal.setData(noise.f, primary_spectrum)

        monitor_spectrum = noise.signal_2_relative_voltage_spectrum
        monitor_signal.setData(noise.f, monitor_spectrum)

        cc_spectrum = noise.cc_relative_voltage_spectrum
        cc.setData(noise.f, np.real(cc_spectrum)) 

        primary_background = [1e-7 / noise.error_signal_1_average for kk in noise.f]
        monitor_background = [1e-7 / noise.error_signal_2_average for kk in noise.f]
        primary_bg.setData(primary_background) 
        monitor_bg.setData(monitor_background)  

        relative_voltage_spectrum.legend.removeItem(primary_signal)
        relative_voltage_spectrum.legend.addItem(primary_signal, f"Primary: {noise.error_signal_1_average}")

        relative_voltage_spectrum.legend.removeItem(monitor_signal)
        relative_voltage_spectrum.legend.addItem(monitor_signal, f"Monitor: {noise.error_signal_2_average}")
        
        frame += 1 # TODO: what if this number gets too big
      
    else:
        pass
win.nextRow()

timer = QtCore.QTimer()
timer.timeout.connect(update_relative_voltage_spectrum)
timer.start(100)

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
    #initial_lock_state = 0
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

def _set_p():
    with device_lock:
        q.set_p_gain(p_gain.value())

with device_lock:
    initial_p = q.get_p_gain()
    #initial_p = 1
p_gain = QtWidgets.QDoubleSpinBox(prefix = "P: ")
p_gain.setMinimum(-np.inf)
p_gain.setMaximum(np.inf)
p_gain.setValue(initial_p)
p_gain.setDecimals(4)
p_gain.setSingleStep(0.001)
p_gain.valueChanged.connect(_set_p)
p_gain_proxy = QtWidgets.QGraphicsProxyWidget()
p_gain_proxy.setWidget(p_gain)
win.addItem(p_gain_proxy, row = 2, col = 1)

def _set_i():
    with device_lock:
        q.set_i_time(i_time.value())

with device_lock:
    initial_i = q.get_i_time()
    #initial_i = 2
i_time = QtWidgets.QDoubleSpinBox(prefix = "I: ")
i_time.setSuffix("us")
i_time.setValue(initial_i)
i_time.setDecimals(1)
i_time.setSingleStep(1)
i_time.valueChanged.connect(_set_i)
i_time_proxy = QtWidgets.QGraphicsProxyWidget()
i_time_proxy.setWidget(i_time)
win.addItem(i_time_proxy, row = 2, col = 2)

def _set_d():
    with device_lock:
        q.set_d_time(d_time.value())

with device_lock:
    initial_d = q.get_d_time()
    #initial_d = 3
d_time = QtWidgets.QDoubleSpinBox(prefix = "D: ")
d_time.setSuffix("us")
d_time.setValue(initial_d)
d_time.setDecimals(1)
d_time.setSingleStep(1)
d_time.valueChanged.connect(_set_d)
d_time_proxy = QtWidgets.QGraphicsProxyWidget()
d_time_proxy.setWidget(d_time)
win.addItem(d_time_proxy, row = 2, col = 3)

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
win.addItem(stop_plots_proxy, row = 2, col = 4)

def _change_averages():
    global averages
    global frame
    averages = averages_button.value()
    frame = 0

averages_button = QtWidgets.QSpinBox(prefix = "Averages: ")
averages_button.setValue(averages)
averages_button.valueChanged.connect(_change_averages)
averages_button_proxy = QtWidgets.QGraphicsProxyWidget()
averages_button_proxy.setWidget(averages_button)
win.addItem(averages_button_proxy, row = 2, col = 5)

def _set_sample_time():
    with device_lock:
        q.set_sample_time(d_time.value())

with device_lock:
    initial_sample_time = q.sample_time()*1e6
    #initial_sample_time= 2

set_sample_time = QtWidgets.QDoubleSpinBox(prefix = "Sample Time: ")
set_sample_time.setSuffix("us")
set_sample_time.setValue(initial_sample_time)
set_sample_time.setDecimals(0)
set_sample_time.setSingleStep(1)
set_sample_time.valueChanged.connect(_set_sample_time)
set_sample_time_proxy = QtWidgets.QGraphicsProxyWidget()
set_sample_time_proxy.setWidget(set_sample_time)
win.addItem(set_sample_time_proxy, row = 2, col = 6)

if __name__ == '__main__':
    pg.exec()
