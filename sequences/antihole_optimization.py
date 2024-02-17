from typing import Any

from onix.sequences.sequence import (
    SegmentEmpty,
    Sequence,
)
from onix.sequences.shared import chasm_segment, detect_segment
from onix.units import ureg

from typing import Any

from onix.models.hyperfine import energies
from onix.sequences.sequence import (
    AWGSinePulse,
    MultiSegments,
    Segment,
)
from onix.awg_maps import get_channel_from_name


def antihole_segment(
    name: str,
    ao_parameters: dict[str, Any],
    eos_parameters: dict[str, Any],
    antihole_parameters: dict[str, Any],
):
    transitions: list[str] = antihole_parameters["transitions"]
    times = antihole_parameters["times"]
    amplitudes = antihole_parameters["amplitudes"]
    total_time = antihole_parameters["total_time"]

    segments = []
    for kk, transition in enumerate(transitions):
        segment = Segment(name + "_" + transition, times[kk])

        ao_freq = ao_parameters["frequency"]
        ao_pulse = AWGSinePulse(ao_freq, amplitudes[kk])
        ao_channel = get_channel_from_name(ao_parameters["name"])
        segment.add_awg_function(ao_channel, ao_pulse)

        eo_parameters = eos_parameters[transition]
        F_state = transition[0]
        D_state = transition[1]
        frequency = (
            energies["5D0"][D_state]
            - energies["7F0"][F_state]
            + eo_parameters["offset"]
        )
        eo_pulse = AWGSinePulse(frequency, eo_parameters["amplitude"])
        eo_channel = get_channel_from_name(eo_parameters["name"])
        segment.add_awg_function(eo_channel, eo_pulse)

        segments.append(segment)

    segment = MultiSegments(name, [segment for segment in segments])
    repeats = int(total_time / segment.duration) + 1
    return (segment, repeats)


class AntiholeOptimization(Sequence):
    def __init__(
        self,
        ao_parameters: dict[str, Any],
        eos_parameters: dict[str, Any],
        chasm_parameters: dict[str, Any],
        antihole_parameters: dict[str, Any],
        detect_parameters: dict[str, Any],
    ):
        super().__init__()
        self._ao_parameters = ao_parameters
        self._eos_parameters = eos_parameters
        self._field_plate_parameters = {"use": False}
        self._chasm_parameters = chasm_parameters
        self._antihole_parameters = antihole_parameters
        self._detect_parameters = detect_parameters
        self._add_optical_segments()
        self._add_helper_segments()

    def _add_optical_segments(self):
        segment, self._chasm_repeats = chasm_segment(
            "chasm",
            self._ao_parameters,
            self._eos_parameters,
            self._field_plate_parameters,
            self._chasm_parameters,
        )
        self.add_segment(segment)

        segment, self._antihole_repeats = antihole_segment(
            "antihole",
            self._ao_parameters,
            self._eos_parameters,
            self._antihole_parameters,
        )
        self.add_segment(segment)

        segment, self.analysis_parameters = detect_segment(
            "detect",
            self._ao_parameters,
            self._eos_parameters,
            self._field_plate_parameters,
            self._detect_parameters,
        )
        self.add_segment(segment)

    def _add_helper_segments(self):
        break_time = 10 * ureg.us
        segment = SegmentEmpty("break", break_time)
        self.add_segment(segment)

    def setup_sequence(self):
        detect_chasm_repeats = self._detect_parameters["chasm_repeats"]
        detect_antihole_repeats = self._detect_parameters["antihole_repeats"]

        segment_repeats = []

        segment_repeats.append(("chasm", self._chasm_repeats))
        segment_repeats.append(("break", 10000))
        segment_repeats.append(("detect", detect_chasm_repeats))

        segment_repeats.append(("antihole", self._antihole_repeats))
        segment_repeats.append(("break", 10000))
        segment_repeats.append(("detect", detect_antihole_repeats))

        return super().setup_sequence(segment_repeats)

    def num_of_records(self) -> int:
        return (
            self._detect_parameters["chasm_repeats"]
            + self._detect_parameters["antihole_repeats"]
        )
