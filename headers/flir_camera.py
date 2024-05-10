from typing import Union
from simple_pyspin import Camera
import numpy as np
from onix.analysis.fitter import Fitter

from PyQt5 import QtWidgets, QtCore, QtGui
import pyqtgraph as pg
import numpy as np
import matplotlib.pyplot as plt

imvOCTTopLeft = None
"""
Must use the FLIR virtual environment. In terminal, run "source ~/.venv/flir/bin/activate". When done, run "deactivate".

Auto-exposure works best in steady state. Program begins with autoexposure off. Best to set exposure yourself, fix the camera with a view of the 
beam and then turn on auto-exposure. This will protect against fluctuations in laser power as your work.

Camera model: FFY-U3-16S2M-CS

http://softwareservices.flir.com/FFY-U3-16S2/latest/Model/public/index.html


Camera class has the following attributes:
   camera_attributes : dictionary
       Contains links to all of the camera nodes which are settable
       attributes.
   camera_methods : dictionary
       Contains links to all of the camera nodes which are executable
       functions.

use cam.camera.camera_attributes.keys to see a full list
"""

def Gaussian2D(xy, amplitude, xo, yo, sigmax, sigmay, bg):
    x, y = xy
    z = bg + amplitude * np.exp( - ((x-xo) ** 2) / (2 * sigmax ** 2) -((y-yo) ** 2) / (2 * sigmay ** 2))
    return z.ravel()


class FLIRCamera:
    def __init__(self, camera_index: Union[int, str] = 0):
        self.camera = Camera(camera_index)

        self.camera.AcquisitionFrameRateAuto = "On"
        self.camera.PixelFormat = "Mono16"
        self.camera.TriggerSource = "Software"
        self.camera.GainAuto = "Off"
        self.camera.Gain = 0
        self.camera.ExposureAuto = "Off"
        self.camera.ExposureMode = "Timed"
        self.camera.ExposureTime = 29
        self.pixel_size = 3.45e-6
        self.pixel_max_brightness = 255  # the camera is 10-bit, but the output is somehow only 8-bit.

        self.camera.init()
        self.height = self.camera.SensorHeight
        self.width = self.camera.SensorWidth
        self.camera.start()
        
        print("Connected to %s %s"%(self.camera.DeviceVendorName, self.camera.DeviceModelName))
        self.status()
        
    def status(self):
        print("Exposure time: %.0f us"%self.camera.ExposureTime)
        print("Gain: %.0f"%self.camera.Gain)
        print("AOI: \n Offset X: %.0f \t Offset Y: %.0f \n Width: %.0f \t Height: %.0f"%(self.camera.OffsetY,self.camera.OffsetX,self.camera.Width,self.camera.Height))
        print("ADC bit depth: %s"%self.camera.AdcBitDepth)
        print("Actual frame rate: %.3f"%(self.camera.AcquisitionResultingFrameRate))

    def get_image(self):
        if self.camera.TriggerSource == "Software":
            self.camera.TriggerSoftware()
        img = self.camera.get_array()
        return img

    def open_live_display(self, auto_range: bool = False, auto_levels: bool = False):
        img_arr = self.get_img_array()
        imvOCTTopLeft.setImage(img_arr, autoRange=auto_range, autoLevels=auto_levels)
        QtCore.QTimer.singleShot(1, self.open_live_display)
        
    def get_exposure(self):
        return self.camera.ExposureTime
        
    def set_exposure(self, exposure):
        """Sets camera exposure from 29 to 30000000 us"""
        self.camera.ExposureTime = exposure
        
    def get_gain(self):
        return self.camera.Gain
        
    def set_gain(self, gain):
        """Sets camera gain from 0 to 30."""
        self.camera.Gain = gain

    def close(self):
        self.camera.stop()
        self.camera.close()


class CameraView(QtWidgets.QWidget):
    # TODO: auto-range and test to ensure that sigma_x and sigma_y are the same x,y as the axes, not inverted

    def __init__(self, camera: FLIRCamera, parent = None):        
        super().__init__(parent)
        self._camera = camera
        self.setWindowTitle("FLIR camera")
        layout = QtWidgets.QGridLayout()

        self.image = pg.ImageView(view=pg.PlotItem())
        layout.addWidget(self.image, 0, 0, 1, 3)

        viewbox = self.image.view
        if not isinstance(viewbox, pg.ViewBox):
            viewbox = viewbox.getViewBox()
        scale = pg.ScaleBar(size=10, suffix = "px")
        scale.setParentItem(viewbox)
        scale.anchor((1, 1), (1, 1), offset=(-20, -20))
        self._running = False
        self._fit = False
        
        self.label = QtWidgets.QLabel("No fit")
        self.label.setFont(QtGui.QFont('Arial', 80)) 
        self.label.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(self.label, 1, 0, 1, 3)

        def autoexposure_button_pressed():
            if self.autoexposure_button.text() == "Auto-exposure Off":
                self.autoexposure = True
                self.autoexposure_button.setText("Auto-exposure On")
            elif self.autoexposure_button.text() == "Auto-exposure On":
                self.autoexposure = False
                self.autoexposure_button.setText("Auto-exposure Off")

        self.min_brightness = 200 # If brightest pixel is below this level, exposure will increase

        self.autoexposure = False
        self.autoexposure_button = QtWidgets.QPushButton()
        self.autoexposure_button.setText("Auto-exposure Off")
        self.autoexposure_button.setFont(QtGui.QFont('Arial', 30)) 
        self.autoexposure_button.clicked.connect(autoexposure_button_pressed)
        layout.addWidget(self.autoexposure_button, 2, 0)


        self.exposure_spinbox = QtWidgets.QSpinBox(prefix = "Exposure: ", suffix = " us")
        self.exposure = self._camera.get_exposure()
        self.exposure_spinbox.setValue(self.exposure)
        self.exposure_spinbox.setSingleStep(1)
        self.exposure_spinbox.editingFinished.connect(self._change_exposure)
        self.exposure_spinbox.setMinimum(29)
        self.exposure_spinbox.setMaximum(30000000)
        self.exposure_spinbox.setFont(QtGui.QFont('Arial', 30)) 
        layout.addWidget(self.exposure_spinbox, 2,1)

        self.gain_spinbox = QtWidgets.QSpinBox(prefix = "Gain: ", suffix = " dB")
        self.gain = self._camera.get_gain()
        self.gain_spinbox.setValue(self.gain)
        self.gain_spinbox.setSingleStep(1)     
        self.gain_spinbox.editingFinished.connect(self._change_gain)
        self.gain_spinbox.setMinimum(0)
        self.gain_spinbox.setMaximum(30)
        self.gain_spinbox.setFont(QtGui.QFont('Arial', 30)) 
        layout.addWidget(self.gain_spinbox, 2,2)

        self.setLayout(layout)

    def start(self, auto_range=False, auto_levels=False):
        self._running = True
        self.update_loop(auto_range, auto_levels)

    def stop(self):
        self._running = True
        self.label.setText("No fit")

    def set_fit_state(self, state):
        self._fit = state
        if not self._fit:
            self.label.setText("No fit")

    def _change_exposure(self):
        self._camera.set_exposure(self.exposure_spinbox.value())
        self.exposure = self.exposure_spinbox.value()

    def _change_gain(self):
        self._camera.set_gain(self.gain_spinbox.value())
        self.gain = self.gain_spinbox.value()
    
    def set_min_brightness(self, val):
        self.min_brightness = val

    def update_loop(self, auto_range=False, auto_levels=False):
        image_raw = np.transpose(self._camera.get_image())
        self.image.setImage(image_raw, autoRange=auto_range, autoLevels=auto_levels)
        if self._fit:
            bin_size = 4
            image = image_raw.reshape(
                len(image_raw) // bin_size,
                bin_size,
                len(image_raw[0]) // bin_size,
                bin_size
            ).sum(3).sum(1)
            x = np.arange(1080 // bin_size)
            y = np.arange(1440 // bin_size)
            x, y = np.meshgrid(x, y)

            fitter = Fitter(Gaussian2D)
            fitter.set_absolute_sigma(False)
            fitter.set_data((x, y), image.ravel())
            j, i = np.unravel_index(image.argmax(), image.shape)
            fitter.set_p0(
                {
                    "amplitude": np.max(image) - np.min(image),
                    "xo": i,
                    "yo": j,
                    "sigmax": 100 / bin_size,
                    "sigmay": 100 / bin_size,
                    "bg": np.mean(image)
                }
            )
            try:
                fitter.fit(maxfev=300)
                sigmax_fit = fitter.results["sigmax"]
                sigmay_fit = fitter.results["sigmay"]
                one_over_e2_fit_x = sigmax_fit * bin_size * self._camera.pixel_size * 2
                one_over_e2_fit_y = sigmay_fit * bin_size * self._camera.pixel_size * 2
                # use 1/e<sup>2</sup><sub style='position: relative; left: -.5em;'>x</sub> for e_x^2 nicely formatted
                fit_label = f"radius<sub>x</sub> = {abs(one_over_e2_fit_x * 1e3):.3f} mm -- radius<sub>y</sub> = {abs(one_over_e2_fit_y * 1e3):.3f} mm"
            except Exception:
                fit_label = "Fitting failed"
            self.label.setText(fit_label)
        if np.max(image_raw) == self._camera.pixel_max_brightness:
            fit_label += ", over-exposed"
            if self.autoexposure:
                self.exposure -= 1
                self.exposure_spinbox.setValue(self.exposure)
                self._change_exposure()
        elif np.max(image_raw) <= self.min_brightness:
            fit_label += ", under-exposed"
            if self.autoexposure:
                self.exposure += 1
                self.exposure_spinbox.setValue(self.exposure)
                self._change_exposure()
            
        if self._running:
            QtCore.QTimer.singleShot(1, self.update_loop) # update every ms

if __name__=="__main__":
    app = QtWidgets.QApplication([])
    cam = FLIRCamera()
    cam.set_gain(0)
    cam.set_exposure(29)

    widget = CameraView(cam)
    widget.show()
    widget.start(auto_levels=False) # "auto-range" should amount to just setting this to be true?
    widget.set_fit_state(True)

    app.exec()