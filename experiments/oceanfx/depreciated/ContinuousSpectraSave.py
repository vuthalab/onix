"""
Code to acquire:
(1) spectra from the oceanFX

while monitoring the cryostat temp.
"""

import time
from datetime import datetime

import os

import numpy as np
import matplotlib.pyplot as plt

import deepdish as dd

from colorama import Fore, Style
from uncertainties import ufloat
parent_dir = "/home/labuser/googledrive/code/Samarium_control/"
os.chdir(parent_dir + "hardware/")
from oceanfx import OceanFX
from headers.util import plot, uarray, nom

#CTC_client = StreamGrabber(port = 5548, topic = 'CTC100', ip_addr='localhost')

LOG_SCALE = False

data_folder = "/home/labuser/non_googledrive_storage/Samarium_clock/Data/2022/09_September_2022/September_26/OceanFX/"
desc = "averaging for OO to wm calibration"


##

spec = OceanFX()

while True:
    # capture spectrum
    os.chdir(parent_dir+'/hardware/')

    meas_time = datetime.now().replace(microsecond=0).isoformat()

    fig = plt.figure(figsize=(13,6))

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

    #temperature = CTC_client.read_on_demand().decode().split(', ')[2]
    #plt.title(f"{desc}, T: {temperature} K")

    fig.savefig(f"{data_folder}spec_{meas_time}_{desc}.png", format = 'png')

    spec_data = {'wavelengths':wavelengths, 'intensities':intensities, 'background':spec.background, 'baseline':spec.baseline}
    dd.io.save(f"{data_folder}spec_{meas_time}_{desc}.h5", spec_data)

    print("Done")


