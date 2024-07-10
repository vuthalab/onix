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
#from headers.oceanfx import OceanFX
from oceanfx import OceanFX
from headers.util import plot, uarray, nom

os.chdir(parent_dir + "/Widgets/python_gui_v2")
from GUIClasses import StreamGrabber

os.chdir(parent_dir + "hardware/")

## User Input

data_folder = "/home/labuser/non_googledrive_storage/Samarium_clock/Data/2022/04_April_2022/April_29/OceanFX/"
desc = "sm_ne"

## Load device
spec = OceanFX()

## Grab background
os.chdir(parent_dir + "hardware/calibration")
background = spec.background

background_new = np.zeros(np.size(background))
for i in range(len(background)):
   background_new[i] = background[i].nominal_value
background = background_new

## Take data

integration_time = 1e6 #1e6
spec._set_integration_time(integration_time)

t0 = time.time()
raw_data = spec._capture_sample2(N_avg = int(1)) # this gives you 8 spectra
t1 = time.time()
print(f'Time taken for measurement is {t1-t0} s')

avg_spectrum = np.mean(raw_data[1],axis = 0)
#avg_spectrum -= background

plt.plot(spec.wavelengths, avg_spectrum)
plt.show()

##

num_of_spectra = 0
for i in range(len(all_data)):
    num_of_spectra += len(all_data[i])

all_data_array = [[]]*num_of_spectra
index = 0
for i in range(len(all_data)):
    for j in range(len(all_data[i])):
        all_data_array[index] = (all_data[i][j] - spec.background*integration_time) / (spec.baseline*integration_time)
        index += 1

for spectrum in all_data_array[0:15]:
    plt.plot(spec.wavelengths, spectrum)
plt.show()

    spec.capture_spectra() # Request up to 15 spectra
# I think the above works, would just need to add uncertainties via
# uarray(samples.mean(axis=0), samples.std(axis=0, ddof=1))

#wavelengths = spec.wavelengths
background = spec.background

# need to remove the background from the spectrum

## Testing integration times
max_integration_time = 10000000 # us = 10 s (set by device)

time_limit = 0.2
log_integration_times = np.linspace(1.3, 5.2, 50)
#        log_integration_times = np.linspace(1.3, 3, 25) # For faster captures (tweaking)

log_integration_times += np.random.uniform(-0.02, 0.02, len(log_integration_times))
integration_times = np.array([
#            10, 11, 12, 13, # Make sure to get hene properly exposed
    *np.power(10, log_integration_times)
], dtype=int)

#integration_times = np.ones(50)*150000

samples = []
for integration_time in integration_times:
    print(f'Capturing spectra at integration time {integration_time/1e6} s')
    sample = spec._capture_samples(
        integration_time,
        time_limit/len(integration_times)
    )
    samples.append(sample)
samples = np.array(samples)

##

while True:
    spec._acquire_samples_mod(integration_time = 100) # this gives you 15 spectra

integration_times, samples = spec._retrieve_samples_mod()

##
spec.cache_spectra(samples,integration_times)
intensities.append(spec.intensities)


#plot(spec.wavelengths,samples[-1]); plt.show()

##
# Capturing spectra
spec = OceanFX()

all_data = []
while True:
    all_data.append(spec._capture_sample_mod(integration_time = 100,time_limit=0.2)) # this gives you 15 spectra

num_of_spectra = 0
for i in range(len(all_data)):
    num_of_spectra += len(all_data[i])

all_data_array = [[]]*num_of_spectra
index = 0
for i in range(len(all_data)):
    for j in range(len(all_data[i])):
        all_data_array[index] = all_data[i][j]
        index += 1

for spectrum in all_data_array[0:500]:
    plt.plot(spectrum)
plt.show()

# I think the above works, would just need to add uncertainties via
# uarray(samples.mean(axis=0), samples.std(axis=0, ddof=1))

wavelengths = spec.wavelength

## Psuedo code
If an Ethernet connection:
Ensure GbE is enabled # otherwise the rate will be 100Mb/s
Set trigger mode = 0 # software trigger (HW triggering can also be used)
Set buffering = enabled
Set number of back-to-back spectra per trigger = 50000
Set integration time = 10 # microseconds
Clear the buffer # optional
SpectrumData[] = new Spectrum[15] # Allocate a buffer to hold the spectra response data
RequestRawSpectrumWithMetadata(15) # Request up to 15 spectra
START_LOOP
    RequestRawSpectrumWithMetadata(15) # Request the next 15 spectra
    SpectrumData = ReadRawSpectrumWithMetadata(15) # Read (up to) the next 15 spectra
# *** Do stuff with the returned spectra here ***
# *** Note: any number of spectra from 0 – 15 may be returned ***
END_LOOP
SpectrumData = ReadRawSpectrumWithMetadata(15) # Read (up to) the last 15 spectra
# *** Do stuff with the returned spectra here ***
# *** Note: any number of spectra from 0 – 15 may be returned ***


##


# Unpack + convert data
test_wavs = []
test_ints = []
for i in range(2):
    test_wavs.append(spec.wavelengths)
    test_ints.append(spec.intensities)
wavelengths = spec.wavelengths
intensities = spec.intensities
background = spec.background
intensities -= background

intensities = []
for i in range(len(samples)):
    temp = samples[i]
    temp -= spec.background
    intensities.append(temp)

fig = plt.figure(figsize=(13,6))

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

temperature = CTC_client.read_on_demand().decode().split(', ')[2]
plt.title(f"{desc}, T: {temperature} K")

#fig.savefig(f"{data_folder}spec_{meas_time}_{desc}_{temperature}.png", format = 'png')


#spec_data = {'temperature':temperature, 'wavelengths':wavelengths, 'intensities':intensities, 'background':spec.background, 'baseline':spec.baseline}
#dd.io.save(f"{data_folder}spec_{meas_time}_{desc}_{temperature}.h5", spec_data)

print("Done")