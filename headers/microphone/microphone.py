import os
import numpy as np
import threading
from onix.headers.microphone import Quarto
from onix.analysis.microphone import Microphone
import time

import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtWidgets
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt

mic = Microphone(num_periods_fit=3, num_periods_save=1, get_data_time=0.5e-3)
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

## Graph
signal = win.addPlot()
signal.setLabel('left', 'microphone signal (V)')
signal.setLabel('bottom', 'time (s)')
#signal.setMouseEnabled(x=False)
signal.setMouseEnabled()
error = signal.plot(pen='y')
# set y axis to be sample number divided by adc_interval (e-6)
def update_signal():
    mic.get_data()
    y_axis = np.arange(0, len(mic.buffer) * mic.adc_interval, mic.adc_interval)
    error.setData(y_axis, mic.buffer)

plots_timer = QtCore.QTimer()
plots_timer.timeout.connect(update_signal)
plots_timer.start(int(mic.get_data_time * 1e3))

if __name__ == '__main__':
    pg.exec()
