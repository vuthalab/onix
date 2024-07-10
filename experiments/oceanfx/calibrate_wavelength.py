"""
Wavelength calibrate bulk spectra from the OceanOptics Spectrometer using a known line.

Code will ask for a folder containing spectra and will resave calibrated spectra in the same folder.

"""
parent_dir = '/home/labuser/googledrive/code/'

import os
import glob
os.chdir(parent_dir + "Samarium_analysis/Widgets")
import deepdish as dd
import scipy.optimize
import tkinter as Tk
import tkinter.filedialog
import numpy as np

def lorentzian(x,amp,wid,cen,b):
    return amp * wid**2 / ((x - cen)**2 + wid**2) + b

def fit_line(known_wav,wavs,ints):
    index = np.argmin(np.abs(wavs - known_wav))
    start_in = index - 25
    end_in = index + 25
    fit_wavs = wavs[start_in:end_in]
    fit_intensities = ints[start_in:end_in]

    popt, pcov = scipy.optimize.curve_fit(lorentzian,fit_wavs,fit_intensities)

    return start_in,end_in,popt,pcov

## Load calibration
# This calibration uses the known value of the hydrogen 656 nm line
known_wavelength = 656.2819

os.chdir(parent_dir + "Samarium_control/hardware/calibration/")
wavelengths,intensities,_ = np.loadtxt('hydrogen_wavelength_calibration_spectrum.txt')

start_in, end_in, popt, pcov = fit_line(known_wavelength, wavelengths, intensities)
amp, wid, cen, b = popt

'''
# Checking the fit once
fit = lorentzian(wavelengths[start_in:end_in], *popt)
plt.plot(wavelengths[start_in:end_in], intensities[start_in:end_in],'o',label='Original Data')
plt.plot(wavelengths[start_in:end_in],fit,label='Fit')
plt.legend()
plt.plot
plt.ylabel('Intensity (counts/μs)')
plt.xlabel('Wavelength (nm)')
'''
delta_wav = cen - known_wavelength # if positive, must subtract from data; if negative, must add to calibrate x axis

## Pick folder
root = Tk.Tk().withdraw()

folder = tkinter.filedialog.askdirectory(initialdir = "/home/labuser/non_googledrive_storage/Samarium_clock/Data/2022")
folder = folder + '/'
print (folder)
os.chdir(folder)

data_folder = folder + "Raw Data/"
calibrated_folder = folder + "Calibrated Data/"

## Calibrate spectra

os.chdir(data_folder)
all_files = [f for f in glob.glob("*.h5")]# get all .h5 files

file_num = 1
for filename in all_files:
    datadict = dd.io.load(data_folder + filename)
    wavelengths = datadict['wavelengths']
    intensities = datadict['intensities']
    print(f'File {file_num} of {len(all_files)+1} loaded successfully...')

    # calibrate
    print(f'Calibrating...')
    if delta_wav > 0:
        wavelengths_new = wavelengths - delta_wav
    else:
        wavelengths_new = wavelengths + delta_wav

    # saving
    print('Saving...')
    os.chdir(calibrated_folder)
    #cal_data = {'temperature':datadict['temperature'], 'wavelengths':wavelengths_new, 'intensities':intensities, 'background':datadict['background'], 'baseline':datadict['baseline']}
    cal_data = {'wavelengths':wavelengths_new, 'intensities':intensities, 'background':datadict['background'], 'baseline':datadict['baseline']}
    dd.io.save(filename[:-3]+'_calibrated.h5', cal_data)

    file_num += 1
