import time

import os

import numpy as np
import matplotlib.pyplot as plt

from colorama import Fore, Style

from uncertainties import ufloat

parent_dir = "/home/labuser/googledrive/code/Samarium_control/"
os.chdir(parent_dir + "hardware/")
#from headers.oceanfx import OceanFX
from oceanfx import OceanFX

from headers.util import plot, uarray, nom


## SETTINGS ##
LOG_SCALE = False


## connect to publisher (spectrometer data)
spec = OceanFX()

# Liveplot
plt.ion()
fig = plt.figure()
while True:
    print('Capturing...')
    spec.capture()

    # Unpack + convert data
    wavelengths = spec.wavelengths
    intensities = spec.intensities
    intensities -= spec.background

    # Intensity
    plot(wavelengths, intensities, continuous=True)
    plt.ylabel('Intensity (counts/μs)')

    if LOG_SCALE:
        plt.yscale('log')
        plt.ylim(1e-6, 1e2)
    else:
        saturation = max(nom(intensities))
        plt.ylim(0, 1.1*saturation)

    plt.xlim(350, 1000)
    plt.xlabel('Wavelength (nm)')

    fig.canvas.draw()

    fig.canvas.flush_events()
    time.sleep(0.1)

