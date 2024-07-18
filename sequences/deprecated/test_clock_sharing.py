from typing import Any
from onix.sequences.sequence import (
    AWGHSHPulse,
    AWGSinePulse,
    AWGSineSweep,
    Segment,
    TTLOn,
)
from onix.models.hyperfine import energies
from onix.sequences.shared import SharedSequence
from onix.awg_maps import get_channel_from_name
import numpy as np
from onix.units import ureg


class ClockSharingTest(SharedSequence):
    """
    Testing clock sharing between AWGs
    Parameters:
    "test_params": {
        "channel1": channel number from 0-3,
        "channel2": channel number from 4-7,
        "amplitude": amplitude of sine pulse,
        "frequency": frequency of sine pulse,
        "duration": duration of the segment
        }
    """

    def __init__(self, parameters: dict[str, Any]):
        super().__init__(parameters, shutter_off_after_antihole=True)
        self._test_params = parameters['test_params']
        self._define_rf()

    def _define_rf(self):
        channel1 = self._test_params["channel1"]
        channel2 = self._test_params["channel2"]
        amplitude = self._test_params["amplitude"]
        frequency = self._test_params["frequency"]
        duration = self._test_params["duration"]

        pulse = AWGSinePulse(frequency, amplitude)
        segment = Segment("rf", duration=duration)

        segment.add_awg_function(channel1, pulse)
        segment.add_awg_function(channel2, pulse)

        self.add_segment(segment)

    def get_rf_sequence(self):
        segment_steps = []
        segment_steps.append(("rf", 1))
        if self._shutter_off_after_antihole:
            segment_steps.append(
                ("shutter_break", self._shutter_rise_delay_repeats))
        detect_cycles = self._detect_parameters["cycles"]["rf"]
        segment_steps.extend(self.get_detect_sequence(detect_cycles))
        self.analysis_parameters["detect_groups"].append(("rf", detect_cycles))
        segment_steps.append(("break", 1))
        segment_steps.append(("break", self._shutter_fall_delay_repeats))
        return segment_steps
