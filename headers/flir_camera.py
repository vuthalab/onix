import time
from simple_pyspin import Camera
import numpy as np
from PIL import Image, ImageTk
import matplotlib.pyplot as plt
import tkinter as tk
import cv2
from onix.analysis.fitter import Fitter
from matplotlib import animation
from matplotlib.patches import Circle
"""
Compatible with a hardware trigger on Line 3 (green = ground; brown = signal)
"""

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
    def __init__(self):
                
        
        
        self.camera = Camera()
        
        self.camera.AcquisitionFrameRateEnable = True
        #self.camera.AcquisitionFrameRate = 60 # Frame rate (FPS)
        self.camera.AcquisitionFrameRate = 400 # Frame rate (FPS)
        self.camera.PixelFormat = 'Mono16' # 16 bit images
        #self.camera.PixelFormat = 'Mono8'
        
        self.camera.init()


        # *** NOTES ***
        # The trigger must be disabled in order to configure whether the source is software or hardware.

        self.camera.TriggerMode = 'Off'
        #self.camera.TriggerSelector = 'AcquisitionStart'
        self.camera.TriggerSelector = 'FrameStart'
        self.camera.TriggerSource = 'Software'
        #self.camera.TriggerSource = 'Line3'
        #self.camera.TriggerActivation = 'LevelHigh'
        #self.camera.TriggerActivation = 'RisingEdge'
        self.camera.TriggerMode = 'On'

        
        self.camera.LineSelector = 'Line2'
        self.camera.LineMode = 'Output'
        self.camera.LineSource = 'ExposureActive'
        
        
        self.camera.GainAuto = 'Off'
        self.camera.Gain = 0 # Set gain (1-10)
        
        
        self.camera.ExposureAuto = 'Off'
        #self.camera.ExposureMode = 'TriggerWidth'
        self.camera.ExposureMode = 'Timed'
        #self.camera.AcquisitionMode = 'SingleFrame'
        #self.camera.AcquisitionMode = 'Continuous'
        self.camera.ExposureTime = 1000 # Microseconds (1 ms)
    
        
        self.height = self.camera.SensorHeight
        self.width = self.camera.SensorWidth
        

        self.camera.start()
        self.camera.cam.AcquisitionStart()
        
        #self.reset_aoi()
        
        print("Connected to %s %s"%(self.camera.DeviceVendorName,self.camera.DeviceModelName))
        self.status()
        
    def status(self):
        #print("Exposure time: %.0f us"%self.camera.ExposureTime)
        print("Gain: %.0f"%self.camera.Gain)
        print("AOI: \n Offset X: %.0f \t Offset Y: %.0f \n Width: %.0f \t Height: %.0f"%(self.camera.OffsetY,self.camera.OffsetX,self.camera.Width,self.camera.Height))
        print("ADC bit depth: %s"%self.camera.AdcBitDepth)
        print("Actual frame rate: %.3f"%(self.camera.AcquisitionResultingFrameRate))
        
        
    def get_img_array(self):
        if self.camera.TriggerSource == 'Software':
            self.camera.TriggerSoftware()
        img = self.camera.get_array()
        return img
        
    def select_aoi(self):
        self.reset_aoi()
        img_arr = self.get_img_array()
        
        r = cv2.selectROI("Select ROI - Press Enter",img_arr,showCrosshair=True,fromCenter=False)
        
        cv2.destroyAllWindows()
        self.set_aoi(r)
        
        
        return r
        
    def select_aoi_v2(self,img_arr):
        r = cv2.selectROI("Select ROI - Press Enter", img_arr,showCrosshair=True,fromCenter=False)
        
        cv2.destroyAllWindows()
        self.set_aoi(r)
        
        return r 
        
    def reset_aoi(self):
        self.camera.stop()
        self.camera.OffsetX = 0
        self.camera.OffsetY = 0
        self.camera.Width = self.camera.WidthMax
        self.camera.Height = self.camera.HeightMax
        self.camera.start()
        
    def set_aoi(self,aoi):
        self.camera.stop()
        self.camera.Width = 4*round(aoi[2]/4)
        self.camera.Height = 4*round(aoi[3]/4)
        self.camera.OffsetX = 4*round(aoi[0]/4)
        self.camera.OffsetY = 4*round(aoi[1]/4)
        self.camera.start()
            
    def snapshot(self):
        img_arr = self.get_img_array()

        plt.imshow(img_arr)
        plt.colorbar()

        plt.show()
        
    def refresh_live_display(self):
        img_arr = self.get_img_array()
        pil_img = (Image.fromarray(img_arr)).resize((int(self.width/2),int(self.height/2)))
        tk_img = ImageTk.PhotoImage(pil_img)
        
        self.img_box.configure(image=tk_img)
        self.img_box.image = tk_img
        
        self.root.after(500,self.refresh_live_display)
        
    def open_live_display(self):
        self.root = tk.Tk()
        self.root.title("FLIR Camera")
        
        self.img_box = tk.Label()
        self.img_box.pack()
        
        
        img_arr = self.get_img_array()
        pil_img = (Image.fromarray(img_arr)).resize((int(self.width/2),int(self.height/2)))
        tk_img = ImageTk.PhotoImage(pil_img)
        
        self.img_box.configure(image=tk_img)
        
        self.root.after(50,self.refresh_live_display)
        self.root.mainloop()
        
    def get_exposure(self):
        return self.camera.ExposureTime
        
    def set_exposure(self,exposure):
        """ set camera expcam.osure in us """
        self.camera.ExposureTime = exposure
        
    def get_gain(self):
        return self.camera.Gain
        
    def set_gain(self,gain):
        """ set camera gain 0 - 30 """
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
                print(f'sigma = {sigmax_fit} \t 1/e^2 radius = {4*3.45e-3*2*sigmax_fit} mm \t time: {end - start}') 
                
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

if __name__=='__main__':
    cam = FLIRCamera()
    
