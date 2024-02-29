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

timer = QtCore.QTimer()
timer.timeout.connect(update_all)
timer.start(50)

# #Untested
# def on_button_pressed():    
#     if lock_state.text() == "Lock On":
#         lock_state.setText("Lock Off")
#         lock_state.setStyleSheet("background-color: Red; color: white;")
#         #q.set_state(0)
#     elif lock_state.text() == "Lock Off":
#         lock_state.setText("Lock On")
#         lock_state.setStyleSheet("background-color: green; color: white;")
#         #q.set_state(1)

# #initial_lock_state = q.get_state()
# # if initial_lock_state == 1:
# #     lock_state = QtWidgets.QPushButton("Lock On")
# # elif initial_lock_state == 0:
# #     lock_state = QtWidgets.QPushButton("Lock Off")
# lock_state = QtWidgets.QPushButton("Lock On")
# lock_state.clicked.connect(on_button_pressed)
# lock_state_proxy = QtWidgets.QGraphicsProxyWidget()
# lock_state_proxy.setWidget(lock_state)
# win.addItem(lock_state_proxy, row = 5, col = 0)

# #no negative numbers allowed on double spinboxes
# def _error_offset():
#     print(f"Error Offset = {error_offset.value()}")
#     #q.set_error_offset(float(error_offset.value())) # TODO: check if float is necessary

# error_offset = QtWidgets.QDoubleSpinBox(prefix = "Error Offset: ")
# error_offset.setDecimals(3) # the params we are setting are floats on the arduino, which can have a total of 6 digits. This level of resolution should suffice
# error_offset.setSingleStep(0.001) # TODO: change the increment size using the mouse position
# error_offset.editingFinished.connect(_error_offset)
# error_offset_proxy = QtWidgets.QGraphicsProxyWidget()
# error_offset_proxy.setWidget(error_offset)
# win.addItem(error_offset_proxy, row = 5, col = 1)

# def _output_offset():
#     print(f"Ouput Offset = {output_offset.value()}")
#     #q.set_output_offset(float(output_offset.value())) # TODO: check if float is necessary

# output_offset = QtWidgets.QDoubleSpinBox(prefix = "Ouput Offset: ")
# output_offset.setDecimals(3) 
# output_offset.setSingleStep(0.001)
# output_offset.editingFinished.connect(_output_offset)
# output_offset_proxy = QtWidgets.QGraphicsProxyWidget()
# output_offset_proxy.setWidget(output_offset)
# win.addItem(output_offset_proxy, row = 5, col = 2)

# def _laser_jump_offset():
#     print(f"Laser Jump Offset = {laser_jump_offset.value()}")
#     # TODO: add laser jump offset to headers

# laser_jump_offset = QtWidgets.QDoubleSpinBox(prefix = "Laser Jump Offset: ")
# laser_jump_offset.setDecimals(3) 
# laser_jump_offset.setSingleStep(0.001) 
# laser_jump_offset.editingFinished.connect(_laser_jump_offset)
# laser_jump_offset_proxy = QtWidgets.QGraphicsProxyWidget()
# laser_jump_offset_proxy.setWidget(laser_jump_offset)
# win.addItem(laser_jump_offset_proxy, row = 5, col = 2)

# def _output_scan():
#     print(f"Output Scan = {output_scan.value()}")
#     # TODO: add output_scan to header

# output_scan = QtWidgets.QDoubleSpinBox(prefix = "Output Scan: ")
# output_scan.setDecimals(3) 
# output_scan.setSingleStep(0.001) 
# output_scan.editingFinished.connect(_output_scan)
# output_scan_proxy = QtWidgets.QGraphicsProxyWidget()
# output_scan_proxy.setWidget(output_scan)
# win.addItem(output_scan_proxy, row = 5, col = 3)

if __name__ == '__main__':
    pg.exec()
