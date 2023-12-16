import numpy as np
from onix.headers.wavemeter.wavemeter import WM


def wavemeter_frequency(channel: int):
    wavemeter = WM()
    freq = wavemeter.read_frequency(channel)
    if isinstance(freq, str):
        return -1
    return freq


def data_averaging(data, sample_rate, pulse_times):
    data_avg = []
    data_err = []

    for run in data:
        scans_avg = []
        scans_err = []

        for pulse in pulse_times:
            start = int(pulse[0] * sample_rate)
            end = int(pulse[1] * sample_rate)

            scans_avg.append(np.mean(run[start: end]))
            scans_err.append(np.std(run[start:end]) / np.sqrt(len(run[start:end])))

        data_avg.append(scans_avg)
        data_err.append(scans_err)

    return np.array(data_avg), np.array(data_err)

