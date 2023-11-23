from typing import Any

from onix.sequences.sequence import (
    AWGSinePulse,
    Sequence,
    Segment,
    SegmentEmpty,
    TTLOn,
)
from onix.sequences.shared import chasm_segment, antihole_segment, detect_segment
from onix.models.hyperfine import energies
from onix.units import Q_, ureg


class RFSpectroscopy(Sequence):
    def __init__(
        self,
        ao_parameters: dict[str, Any],
        eos_parameters: dict[str, Any],
        field_plate_parameters: dict[str, Any],
        chasm_parameters: dict[str, Any],
        antihole_parameters: dict[str, Any],
        rf_parameters: dict[str, Any],
        detect_parameters: dict[str, Any],
    ):
        super().__init__()
        self._ao_parameters = ao_parameters
        self._eos_parameters = eos_parameters
        self._field_plate_parameters = field_plate_parameters
        self._chasm_parameters = chasm_parameters
        self._antihole_parameters = antihole_parameters
        self._rf_parameters = rf_parameters
        self._detect_parameters = detect_parameters
        self._add_optical_segments()
        self._add_rf_segment()
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
            self._detect_parameters
        )
        self.add_segment(segment)

    def _add_rf_segment(self):
        lower_state = self._rf_parameters["transition"][0]
        upper_state = self._rf_parameters["transition"][1]
        frequency = energies["7F0"][upper_state] - energies["7F0"][lower_state] + self._rf_parameters["offset"]
        print("rf", round(frequency, 2))
        segment = Segment("rf", self._rf_parameters["duration"])
        rf_pulse = AWGSinePulse(frequency, self._rf_parameters["amplitude"])
        segment.add_awg_function(self._rf_parameters["channel"], rf_pulse)
        self.add_segment(segment)

    def _add_helper_segments(self):
        break_time = 10 * ureg.us
        segment = SegmentEmpty("break", break_time)
        self.add_segment(segment)

        segment = Segment("field_plate", break_time)
        field_plate_trigger = TTLOn()
        segment.add_ttl_function(self._field_plate_parameters["channel"], field_plate_trigger)
        self.add_segment(segment)

    def setup_sequence(self):
        detect_fast_repeats = self._detect_parameters["fast_repeats"]
        detect_repeats = self._detect_parameters["repeats"]
        field_plate_delay_repeats = 100

        segment_repeats = []

        segment_repeats.append(("chasm", self._chasm_repeats))
        segment_repeats.append(("break", 1))
        segment_repeats.append(("detect", detect_fast_repeats))

        segment_repeats.append(("field_plate", 1))  # trigger the field plate
        segment_repeats.append(("break", field_plate_delay_repeats - 1))  # wait for E field to increase
        segment_repeats.append(("antihole", self._antihole_repeats))
        segment_repeats.append(("break", field_plate_delay_repeats))  # wait for E field to decrease
        segment_repeats.append(("detect", detect_repeats))

        segment_repeats.append(("rf", 1))
        segment_repeats.append(("break", 1))
        segment_repeats.append(("detect", detect_repeats))
        return super().setup_sequence(segment_repeats)

    def num_of_records(self) -> int:
        return self._detect_parameters["fast_repeats"] + 2 * self._detect_parameters["repeats"]
