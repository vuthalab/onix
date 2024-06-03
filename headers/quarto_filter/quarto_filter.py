import os
import numpy as np
import threading
from onix.headers.quarto_filter import Quarto
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtWidgets
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt


app = pg.mkQApp("Low Pass Filter")
q = Quarto("/dev/ttyACM3")

adc_interval = 1e-6 # s; sampling time used by the quarto
interval = 2e-6 # s; how often to ask the quarto for new data
samples = int(interval // adc_interval) # how many data points to ask the quarto for every time
total_intervals = 0.5e4 # how many intervals to plot

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

## Graphs
signal = win.addPlot(title="Quarto Filtered Signal")
signal.setMouseEnabled(x=False)
error = signal.plot(pen='y')

buffer = np.zeros(int(samples* total_intervals))

def update_signal():
    global buffer
    with device_lock:
        data = q.data(samples)
    
    buffer = np.roll(buffer, -samples)
    buffer[-samples:] = data
    error.setData(buffer)

plots_timer = QtCore.QTimer()
plots_timer.timeout.connect(update_signal)
plots_timer.start(int(interval * 1e3))

if __name__ == '__main__':
    pg.exec()
