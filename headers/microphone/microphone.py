import os
import numpy as np
import threading
from onix.headers.microphone import Quarto
from onix.analysis.microphone import Microphone
import time
from onix.analysis.fitter import Fitter
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtWidgets
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt
from scipy.signal import butter, sosfilt



def sine(x, A, omega, phi):
    return A * np.sin(omega*x + phi)


mic = Microphone(num_periods_fit=3, num_periods_save=1, get_data_time=10e-3) # Must be above 8ms
app = pg.mkQApp("Microphone")

device_lock = threading.Lock()

## Start Window
class KeyPressWindow(pg.GraphicsLayoutWidget):
    sigKeyPress = QtCore.pyqtSignal(object)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def keyPressEvent(self, ev):
        self.scene().keyPressEvent(ev)
        self.sigKeyPress.emit(ev)

win = KeyPressWindow(show=True, title="")
win.resize(1000,600)
pg.setConfigOptions(antialias=True)
start_time = time.time()
## Graph
signal = win.addPlot()
signal.setLabel('left', 'microphone signal (V)')
signal.setLabel('bottom', 'time (s)')
signal.setMouseEnabled(y=False)
error = signal.plot(pen='y')

def update_signal():
    current_time = time.time()
    mic.get_data()
    x_axis = np.linspace(0,len(mic.buffer) * mic.adc_interval,len(mic.buffer))

    data = mic.buffer - np.ones(len(mic.buffer)) * np.mean(mic.buffer)
    sos2 = butter(10, 100, 'bandpass', fs=1000, output='sos')
    filtered2 = sosfilt(sos2, data)

    #error.setData(x_axis, np.abs(filtered2))
    #error.setData(x_axis, np.abs(mic.buffer - np.mean(mic.buffer)))
    error.setData(x_axis, mic.buffer)

plots_timer = QtCore.QTimer()
plots_timer.timeout.connect(update_signal)
plots_timer.start(int(mic.get_data_time * 1e3))


if __name__ == '__main__':
    pg.exec()
