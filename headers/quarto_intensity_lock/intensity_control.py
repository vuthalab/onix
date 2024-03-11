from onix.headers.quarto_intensity_lock import Quarto
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtWidgets
import threading
from PyQt5.QtWidgets import *
import numpy as np
from onix.analysis.power_spectrum import CCedPowerSpectrum
import sys
app = pg.mkQApp("Intensity control")
q = Quarto("/dev/ttyACM5")

device_lock = threading.Lock()

win = pg.GraphicsLayoutWidget(show=True, title="")
win.resize(1000,600)
pg.setConfigOptions(antialias=True)

DEFAULT_GET_DATA_LENGTH = 30000

noise = CCedPowerSpectrum(DEFAULT_GET_DATA_LENGTH, q.sample_time, max_points_per_decade=200)

relative_voltage_spectrum = win.addPlot(title="Relative Voltage Spectrum", colspan = 6)
relative_voltage_spectrum.setMouseEnabled(x=False)
relative_voltage_spectrum.setLogMode(x = True,y = True)
relative_voltage_spectrum.addLegend(offset = (50,0))
relative_voltage_spectrum.setLabel("left", text = "Relative power noise density Hz<sup>-1</sup>")
relative_voltage_spectrum.setLabel("bottom", text = "Frequency [Hz]")
signal_1 = relative_voltage_spectrum.plot(pen='y', name = "Signal 1")
#signal_1_index = relative_voltage_spectrum.legend.get_item(signal_1)
signal_2 = relative_voltage_spectrum.plot(pen='r', name = "Signal 2")
cc = relative_voltage_spectrum.plot(pen='g', name = "Cross Correlated")
background = relative_voltage_spectrum.plot(pen='w', name = "Background")
background.setData(np.ones(int(np.ceil(max(noise.f))))*2e-7)  # TODO: not correct.

plots = True
frame = 0
averages = 1
max_int = sys.maxsize
def update_relative_voltage_spectrum():
    global frame
    if plots == True:
        with device_lock:
            primary_data, monitor_data = q.get_both_pd_data()
        if frame < averages:  # TODO: what if the averages is changed lower?
            noise.add_data(primary_data, monitor_data)
        else:
            noise.update_data(primary_data, monitor_data)
        v1_spectrum = noise.signal_1_relative_voltage_spectrum
        signal_1.setData(noise.f, v1_spectrum)
        v2_spectrum = noise.signal_2_relative_voltage_spectrum
        signal_2.setData(noise.f, v2_spectrum)
        cc_spectrum = noise.cc_relative_voltage_spectrum
        cc.setData(noise.f, np.real(cc_spectrum)) # TODO: forced to plot abs of this, as we cannot graph complex things. Why would this be complex at all?
        try:
            frame += 1
        except Exception: 
            frame = averages
      
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
    averages = averages_button.value()

averages_button = QtWidgets.QSpinBox(prefix = "Averages: ")
averages_button.setValue(averages)
averages_button.valueChanged.connect(_change_averages)
averages_button_proxy = QtWidgets.QGraphicsProxyWidget()
averages_button_proxy.setWidget(averages_button)
win.addItem(averages_button_proxy, row = 2, col = 5)

if __name__ == '__main__':
    pg.exec()
