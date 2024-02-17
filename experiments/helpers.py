import numpy as np
from onix.headers.wavemeter.wavemeter import WM


def wavemeter_frequency(channel: int, try_repeat: int = 0):
    """Returns the wavemeter frequency in GHz.
    
    Returns -1 in case of invalid readings.
    Returns -2 in case of other errors.
    """
    try:
        wavemeter = WM()
        freq = wavemeter.read_frequency(channel)
        if isinstance(freq, str):
            for kk in range(try_repeat):
                freq = wavemeter.read_frequency(channel)
            return -1
        return freq
    except Exception:
        return -2


def average_data(data: np.ndarray, sample_rate: float, pulse_times: list[tuple[float, float]]):
    """Averages digitizer data using time intervals.

    Args:
        data: np.array, must be 2-dimensional. The first dimension is repeats (segments).
            The second dimension is time indices.
        sample_rate: float, sample rate per second.
        pulse_times: list of 2-tuples, time intervals to average the data at.

    Returns:
        (data_avg, data_err)
        Both data_avg and data_err has the first dimension as repeats,
        and the second dimension as time interval indices (same length as pulse_times).
    """
    if not isinstance(data, np.ndarray):
        data = np.array(data)
    if not (data.ndim == 2):
        raise ValueError("The input data must be 2-dimensional")

    data_avg = []
    data_err = []

    pulse_times = (np.array(pulse_times) * sample_rate).astype(int)
    for kk in range(len(pulse_times)):
        data_per_pulse = data[:, pulse_times[kk][0]: pulse_times[kk][1]]
        scans_avg = np.average(data_per_pulse, axis=1)
        scans_err = np.std(data_per_pulse, axis=1) / np.sqrt(pulse_times[kk][1] - pulse_times[kk][0])
        data_avg.append(scans_avg)
        data_err.append(scans_err)

    return np.transpose(data_avg), np.transpose(data_err)


def combine_data(datas: list[np.array]):
    """Appends a list of arrays to a single array"""
    datas = np.array(datas)
    return datas.reshape(datas.shape[0] * datas.shape[1], *datas.shape[2:])


def group_data(data: np.ndarray, group_lengths: list[int], non_integer_repeat_error: bool = False):
    """Groups data using the first axis.

    Useful to group segments of digitizer data with labels. For example, for an experiment sequence:
    segment 1 - detection x n1 - segment 2 - detection x n2 - segment 3 - detection x n3, the detection
    is run for (n1 + n2 + n3) times during each repeat, which typically corresponds to (n1 + n2 + n3)
    segments in the digitizer data. If the sequence is run for N times before digitizer readout,
    the total number of segments in the digitizer data is N * (n1 + n2 + n3).
    Calling `group_data(data, [n1, n2, n3])` returns a 3-tuple, with the first element of length N * n1
    corresponds to data from the first detection, the second element of length N * n2 corresponding to data
    from the second detection, and the third element of length N * n3 corresponding to data from the third
    detection.
    """
    data_length = len(data)
    group_length_sum = np.sum(group_lengths)
    if non_integer_repeat_error and data_length % group_length_sum != 0:
        raise ValueError("Data length is not integer divisible by sum of group lengths.")
    masks = []
    remainder_start = 0
    for group_length in group_lengths:
        remainder_end = remainder_start + group_length
        masks.append(
            np.array(
                [
                    kk for kk in range(data_length)
                    if kk % group_length_sum >= remainder_start and kk % group_length_sum < remainder_end
                ]
            )
        )
        remainder_start = remainder_end
    return tuple([data[mask] for mask in masks])

