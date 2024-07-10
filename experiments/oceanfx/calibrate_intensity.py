import time
import itertools
import numpy as np
import matplotlib.pyplot as plt
from colorama import Style
import os
import platform
from onix.headers.oceanfx.oceanfx import OceanFX # type: ignore
from onix.headers.oceanfx.headers.util import nom, std, plot, uarray # type: ignore
import onix.headers.oceanfx.oceanfx as header_file # type: ignore

"""
Background intensity calibration.
"""

spec = OceanFX()
def calibrate(
    name,
    time_limit=60,
    show_plot=False,
):
    print(f'Calibrating OceanFX {name} for {time_limit} seconds...')

    # connect to publisher
    samples = []
    start_time = time.monotonic()

    try:
        for i in itertools.count():
            spec.capture()
            print(f'\rSample {Style.BRIGHT}{i+1}{Style.RESET_ALL}', end='')
            wavelengths = spec.wavelengths
            spectrum = spec.intensities
            samples.append(spectrum)

            if time.monotonic() - start_time > time_limit: break

        samples = samples[1:] # Discard first sample (to avoid 'partial' spectrum).
        spectrum = sum(samples) / len(samples)
        print()


        if show_plot:
            print('Plotting...')
            plot(wavelengths, spectrum, continuous=True)
            plt.xlim(300, 900)
            plt.xlabel('Wavelength (nm)')
            plt.ylabel('Intensity (counts/us)')
            plt.title(name)
            plt.show()

        print(f'Saving {name} OceanFX calibration...')

        header_path = os.path.dirname(header_file.__file__)
        if platform.system() == "Windows":
            calibration_folder_path = header_path + "\calibration"
        elif platform.system() == "Linux":
            calibration_folder_path = header_path + "/calibration"
        os.chdir(calibration_folder_path) 
        np.savetxt(f'{name}.txt', [nom(spectrum), std(spectrum)])
        print('Done.')

    except KeyboardInterrupt:
        #show_interrupt_menu()
        pass



if __name__ == '__main__':
    choice = input('1 for baseline, 2 for background. ')
    if choice == '1':
        input('Unblock OceanFX, then press Enter.')
        calibrate('baseline', show_plot=True)
    elif choice == '2':
        input('Block OceanFX, then press Enter.')
        calibrate('background', time_limit=30, show_plot=True) # time_limit was 120
