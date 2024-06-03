import os
import numpy as np
import threading
from onix.headers.quarto_filter import Quarto
from onix.analysis.pulse_tube_tracker import PulseTubeTracker
import time

import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtWidgets
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt

ptt = PulseTubeTracker()
app = pg.mkQApp("Pulse Tube Tracker")

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
#signal.setMouseEnabled(x=False)
signal.setMouseEnabled()
error = signal.plot(pen='y')

def update_signal():
    ptt._get_data()
    error.setData(ptt.buffer)

plots_timer = QtCore.QTimer()
plots_timer.timeout.connect(update_signal)
plots_timer.start(ptt.get_data_time * 1e3)

if __name__ == '__main__':
    pg.exec()
