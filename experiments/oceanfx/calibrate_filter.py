import time

import numpy as np
#import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from uncertainties import unumpy as unp

from headers.oceanfx import OceanFX
from headers.elliptec_rotation_stage import ElliptecRotationStage

from headers.util import uarray, nom, std, plot

NAME = 'felh0900'
input(f'Calibrating filter {NAME}. Press enter to confirm.')

spec = OceanFX()

mask = (spec.wavelengths > 360) & (spec.wavelengths < 950)
wavelengths = spec.wavelengths[mask]

print('Homing...')
mount = ElliptecRotationStage(port='/dev/rotation_mount_2', offset=38500)
mount.home()


# DEFINE ANGLE RANGE HERE
#angles = np.linspace(0, 30, 61)
#angles = np.linspace(0, 30, 31)
angles = np.linspace(-40, 40, 161)
np.random.shuffle(angles)

#angles = [-30, 30] # For zeroing calibration


##### Collect data #####
data = []

def make_plot():
    """Save plots of current data."""
    data.sort()

    angles, absorption = zip(*data)
    absorption = np.array(absorption)

    plt.figure(figsize=(8, 6))
    for angle, spectrum in zip(angles, absorption):
        if len(angles) > 10 and (round(2*angle) % 10 != 0 or angle < 0): continue
        plot(wavelengths, spectrum, label=f'{angle:.1f}°', clear=False, continuous=True)
    plt.ylabel('Absorption (dB)')
    plt.xlabel('Wavelength (nm)')
    plt.title(f'Absorption vs Wavelength of {NAME.upper()} Filter')
    plt.xlim(min(wavelengths), max(wavelengths))
    plt.ylim(-5, 50)
    plt.legend()
    plt.tight_layout()
#    plt.savefig(f'calibration/filters/{NAME}.pdf')
    plt.savefig(f'calibration/filters/{NAME}.png', dpi=300)
    plt.close()

    plt.figure(figsize=(8, 6))
    plt.imshow(
        nom(absorption)[::-1],
        extent=[min(wavelengths), max(wavelengths), min(angles), max(angles)],
        aspect='auto',
        interpolation='none',
    )
    plt.ylabel('Angle (°)')
    plt.xlabel('Wavelength (nm)')
    plt.title(f'Absorption of {NAME.upper()} Filter')
    cbar = plt.colorbar()
    cbar.ax.set_ylabel('Absorption (dB)')
    plt.tight_layout()
#    plt.savefig(f'calibration/filters/{NAME}-2d.pdf')
    plt.savefig(f'calibration/filters/{NAME}-2d.png', dpi=300)
    plt.close()


def clip(arr):
    return uarray(np.maximum(nom(arr), 1e-8), std(arr))

with open(f'calibration/filters/{NAME}.txt', 'w') as f:
    print('# angle (deg), absorption at each wavelength (dB). First line is wavelengths.', file=f)
    print(9999999999, *wavelengths, file=f)
    for i, angle in enumerate(angles):
        print(i, angle)
        mount.angle = angle

        print('Collecting data...')
        spec.capture()
        transmission = (spec.intensities - spec.background) / spec.baseline
        absorption = -10 * unp.log10(clip(transmission))[mask]

        data.append((angle, absorption))
        print(angle, *nom(absorption), file=f)
        make_plot()
