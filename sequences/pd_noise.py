from typing import Dict

from onix.sequences.sequence import (
    Sequence,
    Segment,
    SegmentEmpty,
    AWGSinePulse,
    TTLPulses
)

from onix.units import Q_, ureg


class pdNoiseMeasurement(Sequence):
    def __init__(
        self,
        ao_parameters: Dict,
        detect_parameters: Dict,
        digitizer_channel: int,):

        super().__init__()

        self._ao_parameters = ao_parameters
        self._detect_parameters = detect_parameters
        self._digitizer_channel = digitizer_channel
        self._add_measurement()

    def _add_measurement(self):
        duration = self._detect_parameters["sample_time"] + self._detect_parameters["buffer"]
        if duration <= 200 * 1e-3:
            self._repeats = 1
            segment = Segment("measurement", duration)

            measurement = AWGSinePulse(self._ao_parameters["frequency"], self._ao_parameters['amplitude'])
            segment.add_awg_function(self._ao_parameters["channel"], measurement)

            TTL = TTLPulses([[1e-3, 2e-3]])
            segment.add_ttl_function(self._digitizer_channel, TTL)

            self.add_segment(segment)

        if duration > 200 * 1e-3:
            self._repeats = int(duration / (200 *1e-3))
            segment = Segment("measurement", 200 * 1e-3)

            measurement = AWGSinePulse(self._ao_parameters["frequency"], self._ao_parameters['amplitude'])
            segment.add_awg_function(self._ao_parameters["channel"], measurement)

            TTL = TTLPulses([[1e-3, 2e-3]])
            segment.add_ttl_function(self._digitizer_channel, TTL)

            self.add_segment(segment)

    def setup_sequence(self):
        return super().setup_sequence([('measurement',self._repeats)])