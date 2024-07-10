"""
Average a bunch of calibrated spectra.

"""
parent_dir = '/home/labuser/googledrive/code/'

import os
import glob
os.chdir(parent_dir + "Samarium_analysis/Widgets")
import deepdish as dd
import matplotlib.pyplot as plt
import scipy.optimize
import numpy as np

from colorama import Fore, Style
from uncertainties import ufloat
parent_dir = "/home/labuser/googledrive/code/Samarium_control/"
os.chdir(parent_dir + "hardware/")
from oceanfx import OceanFX
from headers.util import plot, uarray, nom

import tkinter as Tk
import tkinter.filedialog

## Pick folder
root = Tk.Tk().withdraw()

folder = tkinter.filedialog.askdirectory(initialdir = "/home/labuser/non_googledrive_storage/Europium_tests/Data/2023/02_June_2023/OceanFX")
folder = folder + '/'
print (folder)


## Grab files
os.chdir(folder)
all_files = [f for f in glob.glob("*.h5")]# get all .h5 files

## Gathering spectra

all_spectra = []

file_num = 1
for filename in all_files:
    datadict = dd.io.load(folder + filename)
    wavelengths = datadict['wavelengths']
    intensities = datadict['intensities']
    print(f'File {file_num} of {len(all_files)+1} loaded successfully...')

    all_spectra.append(intensities)

    file_num += 1

print(f'The number of spectra taken is {len(all_spectra)}')

## Average spectra
avg_spectra = np.mean(all_spectra, axis = 0)
desc = '410nm testing average'
data_for_plt = []
for i in range(len(avg_spectra)):
    data_for_plt.append(avg_spectra[i].nominal_value)

spec_data = {'wavelengths':wavelengths, 'avg_spectra':data_for_plt}
dd.io.save(f"{folder}spec_{desc}.h5", spec_data)

## Plotting
# desc = 'OO wm testing average'

fig = plt.figure(figsize = (10,4))
# Intensity
#plot(wavelengths, intensities, continuous=True)
plot(wavelengths, avg_spectra/1e-6, continuous=True,color = 'k')
plt.ylabel('Intensity (counts/s)')

saturation = max(nom(intensities/1e-6))
plt.ylim(0, 1.1*saturation)

plt.xlim(350, 1000)
plt.xlabel('Wavelength (nm)')
plt.tight_layout()
plt.show()

fig.savefig(f"{folder}spec_{desc}.png", format = 'png')

fig.savefig(f"{folder}spec_{desc}.pdf", format = 'pdf')
fig.savefig(f"{folder}spec_{desc}.png", format = 'png')
fig.savefig(f"{folder}spec_{desc}.svg", format = 'svg')


