import numpy as np


def get_correlated_signal(V1: np.ndarray, V2: np.ndarray) -> np.ndarray:
    V1_f = np.fft.fft(V1)
    V2_f = np.fft.fft(V2)
    return np.sqrt(np.abs(np.fft.ifft(np.conjugate(V1_f) * V2_f)))

