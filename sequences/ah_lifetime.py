from typing import Any

from onix.models.hyperfine import energies
from onix.sequences.sequence import (
    Segment,
    TTLOn,
)
from onix.sequences.shared import SharedSequence
from onix.sequences.sequence import AWGSinePulse
from onix.units import ureg


class AHLifetime(SharedSequence):
    def __init__(self, parameters: dict[str, Any]):
        super().__init__(parameters, shutter_off_after_antihole=True)
        self._define_long_break()

    def _define_long_break(self):
        self.long_break_time = 20 * ureg.ms
        segment = Segment("long_break", self.long_break_time)
        segment.add_awg_function(6, AWGSinePulse(121.25e6, self._rf_parameters["amplitude"]))
        self.add_segment(segment)

    def get_antihole_sequence(self):
        segment_steps = super().get_antihole_sequence()

        delta_detect_time = self._detect_parameters["delta_detect_time"]
        delta_detect_time_cycles = int(delta_detect_time / self.long_break_time)
        segment_steps.append(("long_break", delta_detect_time_cycles))

        segment_steps.append(("shutter_break", self._shutter_rise_delay_repeats))
        detect_cycles = self._detect_parameters["cycles"]["antihole_delay"]
        segment_steps.append(("detect", detect_cycles))
        self.analysis_parameters["detect_groups"].append(("antihole_delay", detect_cycles))
        segment_steps.append(("break", self._shutter_fall_delay_repeats))
        return segment_steps

    def get_rf_sequence(self):
        segment_steps = []
        return segment_steps
