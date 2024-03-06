import time
from typing import Union
from simple_pyspin import Camera
import numpy as np
from onix.analysis.fitter import Fitter

from PyQt5 import QtWidgets, QtCore
import pyqtgraph as pg
import numpy as np

imvOCTTopLeft = None

# Camera model: FFY-U3-16S2M-CS

# http://softwareservices.flir.com/FFY-U3-16S2/latest/Model/public/index.html


# Camera class has the following attributes:
 #   camera_attributes : dictionary
 #       Contains links to all of the camera nodes which are settable
 #       attributes.
 #   camera_methods : dictionary
 #       Contains links to all of the camera nodes which are executable
 #       functions.

# use cam.camera.camera_attributes.keys to see a full list

def Gaussian2D(xy, amplitude, xo, yo, sigmax, sigmay, bg):
    x, y = xy
    z = bg + amplitude * np.exp( - ((x-xo) ** 2) / (2 * sigmax ** 2) -((y-yo) ** 2) / (2 * sigmay ** 2))
    return z.ravel()

x = np.arange(1440//4)
y = np.arange(1080//4)

x, y = np.meshgrid(x, y)

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
        
    def set_exposure(self,exposure):
        """Sets camera exposure from 29 to 30000000 us"""
        self.camera.ExposureTime = exposure
        
    def get_gain(self):
        return self.camera.Gain
        
    def set_gain(self,gain):
        """Sets camera gain from 0 to 30."""
        self.camera.Gain = gain

    def beam_waist(self):
        fig, ax = plt.subplots()
        img_arr = self.get_img_array()
        img_arr = img_arr.reshape(len(img_arr)//4, 4, len(img_arr[0])//4, 4).sum(3).sum(1)
        img_arr = img_arr/16
        im = ax.imshow(img_arr, animated = True)
        fitter = Fitter(Gaussian2D)
        fitter.set_absolute_sigma(False)
        
        def worker(frame):
            img_arr = self.get_img_array()
            img_arr = img_arr.reshape(len(img_arr)//4, 4, len(img_arr[0])//4, 4).sum(3).sum(1)
            img_arr = img_arr/16
            fitter.set_data((x, y), img_arr.ravel())
            i,j = np.unravel_index(img_arr.argmax(), img_arr.shape)
            fitter.set_p0({"amplitude": np.max(img_arr) - np.min(img_arr), 
                        "xo": j, 
                        "yo": i, 
                        "sigmax": 50, 
                        "sigmay": 50, 
                        "bg": np.mean(img_arr)})
            
            start = time.time()
            try:
                fitter.fit(maxfev = 200)
                sigmax_fit = fitter.results["sigmax"]
                end = time.time()
                print(f"sigma = {sigmax_fit} \t 1/e^2 radius = {4*3.45e-3*2*sigmax_fit} mm \t time: {end - start}") 
                
            except RuntimeError:
                end = time.time()
                print(f"Fitting failed time: {end  -start}")

            
            im.set_array(img_arr)
            return im,

        ani = animation.FuncAnimation(
            fig=fig,
            func=worker,
            init_func = lambda: None,
            cache_frame_data = False,
            interval = 500,
        )
        plt.show()

    def close(self):
        self.camera.stop()
        self.camera.close()


class CameraView(QtWidgets.QWidget):
    # TODO: fitting, ROI, center_select, plot, overexposure, exposure and gain change, auto exposure.
    def __init__(self, camera: FLIRCamera, parent = None):        
        super().__init__(parent)
        self._camera = camera
        self.setWindowTitle("FLIR camera")
        layout = QtWidgets.QGridLayout()

        self.image = pg.ImageView(view=pg.PlotItem())
        layout.addWidget(self.image, 0, 0)

        viewbox = self.image.view
        if not isinstance(viewbox, pg.ViewBox):
            viewbox = viewbox.getViewBox()
        scale = pg.ScaleBar(size=10, suffix = "px")
        scale.setParentItem(viewbox)
        scale.anchor((1, 1), (1, 1), offset=(-20, -20))
        self._running = False
        self._fit = False

        self.setLayout(layout)

    def start(self, auto_range=False, auto_levels=False):
        self._running = True
        self.update_loop(auto_range, auto_levels)

    def stop(self):
        self._running = True

    def set_fit_state(self, state):
        self._fit = state

    def update_loop(self, auto_range=False, auto_levels=False):
        image = np.transpose(self._camera.get_image())
        self.image.setImage(image, autoRange=auto_range, autoLevels=auto_levels)
        if self._fit:
            bin_size = 4
            image = image.reshape(len(image)//bin_size, bin_size, len(image[0])//bin_size, bin_size).sum(3).sum(1)
            fitter = Fitter(Gaussian2D)
            fitter.set_absolute_sigma(False)
            fitter.set_data((x, y), image.ravel())
            i,j = np.unravel_index(image.argmax(), image.shape)
            fitter.set_p0({"amplitude": np.max(image) - np.min(image), 
                        "xo": j, 
                        "yo": i, 
                        "sigmax": 50, 
                        "sigmay": 50, 
                        "bg": np.mean(image)})
            fitter.fit(maxfev = 200)
            sigmax_fit = fitter.results["sigmax"]
            print(f"sigma = {sigmax_fit} \t 1/e^2 radius = {bin_size*3.45e-3*2*sigmax_fit} mm") 
        if self._running:
            QtCore.QTimer.singleShot(1, self.update_loop)


if __name__=="__main__":
    app = QtWidgets.QApplication([])
    cam = FLIRCamera()
    cam.set_gain(0)
    cam.set_exposure(40)

    widget = CameraView(cam)
    widget.show()
    widget.start(auto_levels=True)
    widget.set_fit_state(True)

    app.exec()