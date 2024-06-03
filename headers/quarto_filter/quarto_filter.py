import os
import numpy as np
import threading
from onix.headers.quarto_filter import Quarto
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtWidgets
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt


app = pg.mkQApp("Filter")
q = Quarto("/dev/ttyACM3")
interval = 3 # ms
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
total_rows = 4

## Graphs
p_error = win.addPlot(title="Quarto Filtered Signal")
p_error.setMouseEnabled(x=False)
error = p_error.plot(pen='y')
def update_p_error(data):
    global error
    error.setData(data)
win.nextRow()

def update_all():
    with device_lock:
        data = q.data(interval * 1000)
    update_p_error(data)

plots_timer = QtCore.QTimer()
plots_timer.timeout.connect(update_all)
plots_timer.start(interval)

if __name__ == '__main__':
    pg.exec()
