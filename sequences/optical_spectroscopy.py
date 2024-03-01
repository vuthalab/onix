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


class OpticalSpectroscopy(SharedSequence):
    def __init__(self, parameters: dict[str, Any]):
        super().__init__(parameters, shutter_off_after_antihole=True)
        self._optical_parameters = parameters["optical"]
        self._define_optical()

    def _define_optical(self):
        transition = self._optical_parameters["transition"]
        eo_channel_name = self._eos_parameters[transition]["name"]
        eo_channel = get_channel_from_name(eo_channel_name)
        lower_state = transition[0]
        upper_state = transition[1]
        offset = self._eos_parameters[transition]["offset"]
        eo_frequency = energies["5D0"][upper_state] - energies["7F0"][lower_state] + offset
        eo_amplitude = self._eos_parameters[transition]["amplitude"]

        ao_amplitude = self._optical_parameters["ao_amplitude"]
        detuning = self._optical_parameters["detuning"]
        ao_frequency = self._ao_parameters["center_frequency"] + detuning / self._ao_parameters["order"]

        duration = self._optical_parameters["duration"]

        segment = Segment("optical", duration=duration)
        eo_pulse = AWGSinePulse(eo_frequency, eo_amplitude)
        segment.add_awg_function(eo_channel, eo_pulse)
        ao_channel = get_channel_from_name(self._ao_parameters["name"])
        ao_pulse = AWGSinePulse(ao_frequency, ao_amplitude)
        segment.add_awg_function(ao_channel, ao_pulse)
        self.add_segment(segment)

    def get_rf_sequence(self):
        segment_steps = []
        segment_steps.append(("optical", 1))
        segment_steps.append(("shutter_break", self._shutter_rise_delay_repeats))
        detect_cycles = self._detect_parameters["cycles"]["rf"]
        segment_steps.append(("detect", detect_cycles))
        self.analysis_parameters["detect_groups"].append(("rf", detect_cycles))
        if self._shutter_off_after_antihole:
            segment_steps.append(("break", self._shutter_fall_delay_repeats))
        return segment_steps
