from typing import Any
from onix.sequences.sequence import (
    Sequence,
)
from onix.sequences.shared import chasm_segment


class RFChasm(Sequence):
    def __init__(
        self,
        ao_parameters: dict[str, Any],
        eos_parameters: dict[str, Any],
        field_plate_parameters: dict[str, Any],
        chasm_parameters: dict[str, Any]
    ):
        super().__init__()
        self._ao_parameters = ao_parameters
        self._eos_parameters = eos_parameters
        self._field_plate_parameters = field_plate_parameters
        self._chasm_parameters = chasm_parameters
        self._add_optical_segments()

    def _add_optical_segments(self):
        segment, self._chasm_repeats = chasm_segment(
            "chasm",
            self._ao_parameters,
            self._eos_parameters,
            self._field_plate_parameters,
            self._chasm_parameters,
        )
        self.add_segment(segment)

    def setup_sequence(self):
        segment_repeats = []
        segment_repeats.append(("chasm", self._chasm_repeats))
        return super().setup_sequence(segment_repeats)
