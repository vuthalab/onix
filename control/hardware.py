import numpy as np
from onix.units import Q_, ureg

AWG_SAMPLE_RATE = 625e6
AWG_MIN_SEGMENT_SAMPLE = 96  # for 4 channels only
AWG_SEGMENT_SIZE_MULTIPLE = 32  # for 4 channels only

AWG_BOARD_COUNT = 2


def voltage_to_awg_amplitude(voltage_amplitude: Q_):
    """Converts voltage amplitude to AWG amplitude"""
    max_voltage_amplitude = 2.5 * ureg.V
    max_awg_amplitude = 2 ** 15
    return int(voltage_amplitude / max_voltage_amplitude * max_awg_amplitude)

