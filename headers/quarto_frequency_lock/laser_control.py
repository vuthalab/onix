import numpy as np
from onix.headers.quarto_frequency_lock import Quarto

import pyqtgraph as pg
from pyqtgraph.Qt import QtCore
from PyQt5.QtWidgets import *  

app = pg.mkQApp("Laser control")
q = Quarto("/dev/ttyACM2")

win = pg.GraphicsLayoutWidget(show=True, title="")
win.resize(1000,600)
pg.setConfigOptions(antialias=True)

LENGTH = 1000

p_error = win.addPlot(title="error signal")
p_error.setMouseEnabled(x=False)
error = p_error.plot(pen='y')
def update_p_error(data):
    global error
    error.setData(data)
win.nextRow()

p_output = win.addPlot(title="output signal")
p_output.setMouseEnabled(x=False)
output = p_output.plot(pen='y')
def update_p_output(data):
    global output
    output.setData(data)
win.nextRow()

p_transmission = win.addPlot(title="transmission signal")
p_transmission.setMouseEnabled(x=False)
transmission = p_transmission.plot(pen='y')
def update_p_transmission(data):
    global transmission
    transmission.setData(data)
win.nextRow()

p_cavity_error = win.addPlot(title="cavity error signal")
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

# Untested
# def on_button_pressed():    
#     if lock_state.text() == "Lock On":
#         lock_state.setText("Lock Off")
#         lock_state.setStyleSheet("background-color: Red; color: white;")
#         # TODO: insert command to change the quarto state
#     elif lock_state.text() == "Lock Off":
#         lock_state.setText("Lock On")
#         lock_state.setStyleSheet("background-color: green; color: white;")
#         # TODO: insert command to change the quarto state

# lock_state = QtWidgets.QPushButton("Lock On")
# lock_state.clicked.connect(on_button_pressed)

# proxy = QtWidgets.QGraphicsProxyWidget()
# proxy.setWidget(lock_state)
# win.addItem(proxy)

# win.nextRow()

# def spinbox():
#     print(param.value())

# param_label = QLabel("Param")

# param = QtWidgets.QDoubleSpinBox()
# param.setDecimals(3)
# param.setSingleStep(0.001) # TODO: change the increment size using the mouse position
# param.editingFinished.connect(spinbox)

# proxy1 = QtWidgets.QGraphicsProxyWidget()
# proxy1.setWidget(param)
# win.addItem(proxy1)


# proxy2 = QtWidgets.QGraphicsProxyWidget()
# proxy2.setWidget(param_label)
# win.addItem(proxy2)

if __name__ == '__main__':
    pg.exec()
