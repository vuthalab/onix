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

#method = "low_pass" # data, low pass, band pass, FFT, IFFT

mic = Microphone(num_periods_fit=3, num_periods_save=1, get_data_time=10e-3) # Must be above 8ms


app = pg.mkQApp("Microphone")
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

# if method == "FFT":
#     signal.setLabel('left', 'Relative Voltage Noise Density (1/sqrt(Hz))')
#     signal.setLabel('bottom', 'Frequency (Hz)')
# else:
signal.setLabel('left', 'microphone signal (V)')
signal.setLabel('bottom', 'time (s)')
signal.setMouseEnabled()
error = signal.plot(pen='y')
def update_signal():
    mic.get_data()
    #mic.windowed_average(N = 5000)
    x_axis = np.linspace(0,len(mic.buffer) * mic.adc_interval,len(mic.buffer))
    error.setData(x_axis, mic.buffer)
    #data = mic.buffer - np.ones(len(mic.buffer)) * np.mean(mic.buffer)
    #sos2 = butter(10, 100, 'bandpass', fs=1000, output='sos')
    #filtered2 = sosfilt(sos2, data)

    #error.setData(x_axis, np.abs(filtered2))
    #error.setData(x_axis, np.abs(mic.buffer - np.mean(mic.buffer)))
    #error.setData(mic.buffer)
    #error.setData(mic.f, mic.relative_voltage_spectrum)
    #error.setData(mic.inverse_fft)
    #mic.fill_buffer()
    #error.setData(mic.voltage_spectrum)

plots_timer = QtCore.QTimer()
plots_timer.timeout.connect(update_signal)
plots_timer.start(int(mic.get_data_time * 1e3))
#plots_timer.start(int(2.4e3))


if __name__ == '__main__':
    pg.exec()

