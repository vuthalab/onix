from onix.analysis.pulse_tube_tracker import PulseTubeTracker
import matplotlib.pyplot as plt
import numpy as np

def sine(x,A,omega,phi):
    return A * np.sin(omega * x + phi)

ptt = PulseTubeTracker()
for i in range(8000):
    ptt._get_data()

plt.scatter(ptt.t_axis, ptt.buffer, s = 1)
plt.title("Raw data")
plt.show()

ptt._get_fit()
print(ptt.A, ptt.omega, ptt.phi)
plt.plot(ptt.t_axis, sine(ptt.t_axis, ptt.A, ptt.omega, ptt.phi), alpha = 0.5)
plt.plot(ptt.t_axis, ptt.buffer, alpha = 0.5)
plt.show()



















































"""
q = Quarto()
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

buffer = np.zeros(int(1e6)) # display 1e6 samples = 1 s
signal = win.addPlot()
signal.setMouseEnabled()
error = signal.plot(pen='y')

def update_signal():
    global buffer
    buffer = np.roll(buffer, -5000)
    buffer[-5000:] = q.data(5000)
    error.setData(buffer)

plots_timer = QtCore.QTimer()
plots_timer.timeout.connect(update_signal)
plots_timer.start(5)

if __name__ == '__main__':
    pg.exec()
"""

