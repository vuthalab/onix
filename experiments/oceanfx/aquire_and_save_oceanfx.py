import os
import numpy as np
from datetime import date
import matplotlib.pyplot as plt
from colorama import Fore, Style
from onix.headers.oceanfx.oceanfx import OceanFX
from onix.headers.oceanfx.headers.util import plot, nom
import deepdish as dd
LOG_SCALE = False

spec = OceanFX()
#spec.capture()

# Unpack + convert data
wavelengths = spec.wavelengths
intensities = spec.intensities
intensities -= spec.background

# Intensity
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
plt.show()

#data = np.column_stack((np.array(wavelengths, dtype = float), np.array(intensities, dtype = float)))
t = date.today()
#t = datetime.now().replace(microsecond=0)
# os.chdir(r"c:\Users\onix\Downloads")
# np.savetxt(f"OceanFX Spectra {t}", data, delimiter=",", header = "Wavelength (nm), bg subtracted intensity (counts/us)", comments="parameters")

import pandas as pd
df = pd.DataFrame(np.column_stack([wavelengths, intensities]), 
                               columns=['Wavelength(nm)', 'Intensity (counts / us)'])
print(df)
df.to_csv(f"OceanFX Spectra")

spec_data = {'wavelengths':wavelengths, 'intensities':intensities, 'background':spec.background, 'baseline':spec.baseline}
dd.io.save(f"OceanFX Spectra {t}.h5", spec_data)