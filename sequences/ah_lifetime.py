from typing import Any

from onix.models.hyperfine import energies
from onix.sequences.sequence import (
    Segment,
    TTLOn,
)
from onix.sequences.shared import SharedSequence
from onix.units import ureg


class AHLifetime(SharedSequence):
    def __init__(self, parameters: dict[str, Any]):
        super().__init__(parameters, shutter_off_after_antihole=False)

    def _define_long_break(self):
        self.long_break_time = 20 * ureg.ms
        segment = Segment("shutter_long_break", self.long_break_time)
        segment.add_ttl_function(self._shutter_parameters["channel"], TTLOn())
        self.add_segment(segment)
    
    def get_antihole_sequence(self):
        segment_steps = super().get_antihole_sequence()

        delta_detect_time = self._detect_parameters["delta_detect_time"]
        delta_detect_time_cycles = int(delta_detect_time / self.long_break_time)
        segment_steps.append("shutter_long_break", delta_detect_time_cycles)

        detect_cycles = self._detect_parameters["cycles"]["antihole_delay"]
        segment_steps.append(("detect", detect_cycles))
        self.analysis_parameters["detect_groups"].append(("antihole_delay", detect_cycles))
        segment_steps.append(("break", self._shutter_fall_delay_repeats))
        return segment_steps

    def get_rf_sequence(self):
        segment_steps = []
        return segment_steps
    