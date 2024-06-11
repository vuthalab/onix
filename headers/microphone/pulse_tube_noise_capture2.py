from onix.headers.microphone import Quarto
from onix.analysis.fitter import Fitter

import numpy as np
import matplotlib.pyplot as plt
import time

from pprint import pprint

from scipy.signal import find_peaks
from scipy.optimize import curve_fit

q = Quarto()
adc_interval = q.adc_interval   # [s]
sample_rate = 1/adc_interval    # [samples per second]

datas = {i: q.data() for i in range(7)}

pprint(datas)