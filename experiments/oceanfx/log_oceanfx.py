import sys
import time
import itertools
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt

from colorama import Fore, Style

from headers.oceanfx import OCEANFX_WAVELENGTHS
from headers.zmq_client_socket import connect_to

from headers.util import uarray, nom, std, plot



if len(sys.argv) > 1:
    DURATION = float(sys.argv[1])
    print(f'Collecting data for {DURATION:.1f} hours.')
else:
    DURATION = None
    print('Collecting data indefinitely.')



##### Parameters #####
root_dir = Path('~/Desktop/edm_data/logs/oceanfx/').expanduser()
log_file = root_dir / (time.strftime('%Y-%m-%d %H꞉%M꞉%S') + '.txt')

N = 4 # number of samples to average. Each 'sample' is actually several captures, see publisher.




## connect to publisher
monitor_socket = connect_to('spectrometer')


start_time = time.monotonic()

def format_array(arr): return ' '.join(f'{x:.6f}' for x in arr)
with open(log_file, 'a') as f:
    print(format_array(OCEANFX_WAVELENGTHS), file=f)
    for n in itertools.count(1):
        samples = []

        # Average a few samples
        for i in range(N):
            print(f'\r{Fore.YELLOW}Capture {n}{Style.RESET_ALL}: {100*(i+1)/N:.0f}%', end='')
            _, data = monitor_socket.blocking_read()
            sample = data['intensities']
            samples.append(uarray(sample['nom'], sample['std']))
        print(f'  [{Fore.GREEN}SAVED{Style.RESET_ALL}]')

        spectrum = sum(samples) / len(samples)
        print(time.time(), format_array(nom(spectrum)), format_array(std(spectrum)), file=f)

        if DURATION is not None and time.monotonic() - start_time > DURATION * 3600:
            break
