"""
Zoom in and fit a Lorentzian to a selected peak

"""
parent_dir = '/home/labuser/googledrive/code/'

import os
import glob
os.chdir(parent_dir + "Samarium_analysis/Widgets")
import deepdish as dd
import matplotlib.pyplot as plt
import scipy.optimize
import numpy as np

import tkinter as Tk
import tkinter.filedialog

from mpl_point_clicker import clicker

def lorentzian(x,amp,wid,cen,b):
    return amp * wid**2 / ((x - cen)**2 + wid**2) + b

def voigt(x,ampG,sigmaG,cenG,ampL,cenL,widL,b):
    return (ampG*(1/(sigmaG*(np.sqrt(2*np.pi))))*(np.exp(-((x-cenG)**2)/((2*sigmaG)**2)))) +\
           ((ampL*widL**2/((x-cenL)**2+widL**2)) )

def fit_line(known_wav,wavs,ints):
    index = np.argmin(np.abs(wavs - known_wav))
    start_in = index - 25 # impirically measured good window = 50 points
    end_in = index + 25
    fit_wavs = wavs[start_in:end_in]
    fit_intensities = ints[start_in:end_in]

    popt, pcov = scipy.optimize.curve_fit(lorentzian,fit_wavs,fit_intensities,p0=[max(fit_intensities),2,known_wav,0])

    return start_in,end_in,popt,pcov

## Pick file
root = Tk.Tk().withdraw()

filename = tkinter.filedialog.askopenfile(initialdir = "/home/labuser/non_googledrive_storage/Samarium_clock/Data/2022")
filename = filename.name
folder = filename.split('spec')[0]
filename = 'spec' + filename.split('spec')[1]
print (filename)
os.chdir(folder)

## Load file
datadict = dd.io.load(folder + filename)
wavelengths = datadict['wavelengths']
intensities_new = datadict['intensities']

#if type(intensities) == '<class 'numpy.ndarray'>':
#   intensities_new = intensities

intensities_new = np.zeros(np.size(intensities))
for i in range(len(intensities)):
   intensities_new[i] = intensities[i].nominal_value

## Choose peak
fig,ax = plt.subplots(figsize=(13,6))
ax.plot(wavelengths,intensities_new)
ax.set_xlabel('Wavelength (nm)')
ax.set_ylabel('Intensity (counts/μs)')
ax.set_xlim([500,800])
ax.set_title('Click which peak you would like to fit...(choose only one)')
click_tracker = clicker(ax,["event"],markers=['x'])
plt.show()

#plt.pause(25)

## Fitting
#zoom_wav = click_tracker.get_positions()['event'][0][0]
zoom_wav = 642

start_in, end_in, popt, pcov = fit_line(zoom_wav, wavelengths, intensities_new)
# look at uncertainty in cen
delta_popt = np.array([np.sqrt(pcov[i,i]) for i in range(len(popt))])

x = wavelengths[start_in:end_in]
y = intensities_new[start_in:end_in]
Navg = 1
yerr = np.std(intensities_new[start_in:end_in], axis = 0)/np.sqrt(Navg)

fit = lorentzian(x, *popt)
residuals = y - fit
wssr = np.sum(residuals**2/yerr**2)
dof = len(y) - len(popt)
reduced_chi_squared = wssr/dof
expanded_delta_popt = delta_popt * np.sqrt(reduced_chi_squared)

amp,wid,cen,b = popt
amp_err, wid_err, cen_err, b_err = expanded_delta_popt

print ('The Lorentizan fitted peak wavelength ' + str(round(cen,3)) + '+/-' + str(round(cen_err,3)) + ' nm')

from scipy.constants import c

# Checking the fit once
fig,ax = plt.subplots(figsize=(13,6))
plt.plot(wavelengths[start_in:end_in], intensities_new[start_in:end_in],'o',label='Original Data')
plt.plot(wavelengths[start_in:end_in],fit,label='Fit')
plt.text(min(wavelengths[start_in:end_in]),0.9*max(intensities_new[start_in:end_in]),'The Lorentizan fitted peak wavelength ' + str(round(cen,3)) + '+/-' + str(round(cen_err,3)) + ' nm \n or ' + str(round(c/cen))+ '+/-' + str(round(abs(c/(cen+cen_err)-(c/(cen-cen_err))))) + ' GHz')
plt.legend()
plt.plot
plt.ylabel('Intensity (counts/μs)')
plt.xlabel('Wavelength (nm)')
plt.show()

#fig.savefig(filename.split('.')[0]+f"_zoom_{round(zoom_wav)}.png", format = 'png')
