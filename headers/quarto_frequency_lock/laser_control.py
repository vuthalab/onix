import numpy as np
from onix.headers.quarto_frequency_lock import Quarto

import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtWidgets
from PyQt5.QtWidgets import *  

app = pg.mkQApp("Laser control")
q = Quarto("/dev/ttyACM2")

win = pg.GraphicsLayoutWidget(show=True, title="")
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


warning = QtWidgets.QPushButton()
warning_proxy = QtWidgets.QGraphicsProxyWidget()
warning_proxy.setWidget(warning)
warning.setStyleSheet("color: white")
win.addItem(warning_proxy, row = 5, col = 3)

def update_all():
    data = q.get_all_data()
    # data = {
    #     "error": np.ones(1000), 
    #     "output": np.ones(1000),
    #     "transmission": np.ones(1000),
    #     "cavity_error": np.ones(1000)
    # }
    update_p_error(data["error"])
    update_p_output(data["output"])
    update_p_transmission(data["transmission"])
    update_p_cavity_error(data["cavity_error"])

    integral_warning, output_warning = q.output_limit_indicator()
    
    if integral_warning == "Integrator good" and output_warning == "Output good":
        warning.setStyleSheet("background-color: green")
        warning_text = "Warnings Good"
    else: 
        warning.setStyleSheet("background-color: red")
        warning_text = integral_warning + " " + output_warning

    warning.setText(warning_text)
    

timer = QtCore.QTimer()
timer.timeout.connect(update_all)
timer.start(50)


def on_button_pressed():    
    if lock_state.text() == "Lock On" or lock_state.text() == "Autorelock On":
        lock_state.setText("Lock Off")
        lock_state.setStyleSheet("background-color: Red; color: white;")
        q.set_state(0)
    elif lock_state.text() == "Lock Off":
        lock_state.setText("Autorelock On")
        lock_state.setStyleSheet("background-color: green; color: white;")
        q.set_state(2)

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
win.addItem(lock_state_proxy, row = 5, col = 0)

def _offset():
    print(f"Offset = {offset.value()}")
    q.set_output_offset(float(offset.value())) # TODO: check if float is necessary

initial_offset = q.get_output_offset
offset = QtWidgets.QDoubleSpinBox(prefix = "Offset: ")
offset.setValue(initial_offset)
offset.setDecimals(2) 
offset.setSingleStep(0.01)
offset.editingFinished.connect(_offset)
offset.setMinimum(-10)
offset.setMaximum(10) #TODO: set maximum
offset_proxy = QtWidgets.QGraphicsProxyWidget()
offset_proxy.setWidget(offset)
win.addItem(offset_proxy, row = 5, col = 1)

def _scan():
    q.set_scan(float(scan.value()))

scan = QtWidgets.QDoubleSpinBox(prefix = "Scan: ")
initial_scan = q.get_scan()
scan.setValue(initial_scan)
scan.setDecimals(2) 
scan.setSingleStep(0.01) 
scan.editingFinished.connect(_scan)
scan.setMinimum(0)
#scan.setMaximum() #TODO: set maximum
scan_proxy = QtWidgets.QGraphicsProxyWidget()
scan_proxy.setWidget(scan)
win.addItem(scan_proxy, row = 5, col = 2)

if __name__ == '__main__':
    pg.exec()
