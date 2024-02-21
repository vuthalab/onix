from typing import Any

from onix.models.hyperfine import energies
from onix.sequences.sequence import (
    AWGConstant,
    AWGSinePulse,
    Segment,
    TTLOn,
)
from onix.sequences.shared import SharedSequence
from onix.units import ureg
from onix.awg_maps import get_channel_from_name


class RFSpectroscopy(SharedSequence):
    def __init__(self, parameters: dict[str, Any]):
        super().__init__(parameters, shutter_off_after_antihole=True)
        self._define_rf()

    def _define_rf(self):
        rf_channel = get_channel_from_name(self._rf_parameters["name"])
        lower_state = self._rf_parameters["transition"][0]
        upper_state = self._rf_parameters["transition"][1]
        offset = self._rf_parameters["offset"]
        center_frequency = energies["7F0"][upper_state] - energies["7F0"][lower_state] + offset
        detuning = self._rf_parameters["detuning"]
        duration = self._rf_parameters["duration"]
        amplitude = self._rf_parameters["amplitude"]
        segment = Segment("rf", duration=duration)
        pulse = AWGSinePulse(center_frequency + detuning, amplitude)
        segment.add_awg_function(rf_channel, pulse)
        if self._shutter_off_after_antihole:
            segment.add_ttl_function(self._shutter_parameters["channel"], TTLOn())
        self.add_segment(segment)

    def get_rf_sequence(self):
        # the shutter is open (high) at the beginning of this function.
        segment_steps = []
        segment_steps.append(("rf", 1))
        detect_cycles = self._detect_parameters["cycles"]["rf"]
        segment_steps.append(("detect", detect_cycles))
        self.analysis_parameters["detect_groups"].append(("rf", detect_cycles))
        segment_steps.append(("break", 1))
        segment_steps.append(("break", self._shutter_fall_delay_repeats))
        return segment_steps
