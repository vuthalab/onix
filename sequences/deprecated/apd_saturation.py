from typing import Dict

from onix.sequences.sequence import (
    Sequence,
    Segment,
    AWGSinePulse,
    TTLPulses,
)
from onix.units import Q_, ureg


class APDSaturation(Sequence):
    def __init__(
        self,
        ao_parameters: Dict,
        detect_ao_parameters: Dict,
        digitizer_channel: int,
        saturation_time: Q_,
        detection_time: Q_,
    ):
        super().__init__()
        self._ao_parameters = ao_parameters
        self._detect_ao_parameters = detect_ao_parameters
        self._digitizer_channel = digitizer_channel
        self._saturation_time = saturation_time
        self._detection_time = detection_time
        self._add_saturation_pulse()

    def _add_saturation_pulse(self):
        duration = 1 * ureg.ms
        self._saturation_repeats = int(self._saturation_time / duration)
        segment = Segment("saturation", duration)
        ao_pulse = AWGSinePulse(self._ao_parameters["frequency"], self._ao_parameters["amplitude"])
        segment.add_awg_function(self._ao_parameters["channel"], ao_pulse)
        detect_ao_pulse = AWGSinePulse(self._detect_ao_parameters["frequency"], self._detect_ao_parameters["amplitude"])
        segment.add_awg_function(self._detect_ao_parameters["channel"], detect_ao_pulse)
        self.add_segment(segment)

        segment = Segment("detect")
        ttl_function = TTLPulses([[0, 4e-6]])
        segment.add_ttl_function(self._digitizer_channel, ttl_function)
        self.add_segment(segment)
        self.detect_time = self._saturation_time + self._detection_time

    def setup_sequence(self):
        return super().setup_sequence([("detect", 1), ("saturation", self._saturation_repeats)])
