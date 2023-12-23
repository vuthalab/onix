from functools import partial
import numbers
from typing import Any, Union

import numpy as np

from onix.models.hyperfine import energies
from onix.sequences.sequence import (
    AWGConstant,
    AWGFunction,
    Segment,
    SegmentEmpty,
    Sequence,
)
from onix.sequences.shared import antihole_segment, chasm_segment, detect_segment
from onix.units import ureg, Q_
from onix.awg_maps import get_channel_from_name


class AWGPulse(AWGFunction):
    def __init__(
        self,
        pulse_time: Union[float, Q_],
        frequency: Union[float, Q_],
        amplitude: float,
        phase: float,
    ):
        super().__init__()
        self._pulse_time = pulse_time
        self._frequency = frequency
        self._amplitude = amplitude
        self._phase = phase

    def output(self, times):
        def sine(times, frequency, amplitude, phase):
            return amplitude* np.sin(2 * np.pi * frequency * times + phase)

        return sine(times, self._frequency, self._amplitude, self._phase)

    @property
    def min_duration(self) -> Q_:
        return self._pulse_time

    @property
    def max_amplitude(self):
        return self._amplitude

class RFSpinEchoLongDelay(Sequence):
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

        self._antihole_segments_and_repeats = antihole_segment(
            "antihole",
            self._ao_parameters,
            self._eos_parameters,
            self._field_plate_parameters,
            self._antihole_parameters,
            return_separate_segments=True,
        )
        for segment, repeats in self._antihole_segments_and_repeats:
            self.add_segment(segment)

        segment, self.analysis_parameters = detect_segment(
            "detect",
            self._ao_parameters,
            self._eos_parameters,
            self._field_plate_parameters,
            self._detect_parameters,
        )
        self.add_segment(segment)

    def _add_rf_segment(self):
        lower_state = self._rf_parameters["transition"][0]
        upper_state = self._rf_parameters["transition"][1]
        frequency = (
            energies["7F0"][upper_state]
            - energies["7F0"][lower_state]
            + self._rf_parameters["offset"]
            + self._rf_parameters["detuning"]
        )
        piov2_time = self._rf_parameters["piov2_time"]
        pi_time = self._rf_parameters["pi_time"]
        phase = self._rf_parameters["phase"]
        amplitude = self._rf_parameters["amplitude"]

        segment = Segment("piov2_pulse")
        piov2_pulse = AWGPulse(
            piov2_time,
            frequency,
            amplitude,
            0,
        )
        rf_channel = get_channel_from_name(self._rf_parameters["name"])
        segment.add_awg_function(rf_channel, piov2_pulse)
        self.add_segment(segment)

        segment = Segment("pi_pulse")
        pi_pulse = AWGPulse(
            pi_time,
            frequency,
            amplitude,
            phase,
        )
        segment.add_awg_function(rf_channel, pi_pulse)
        self.add_segment(segment)

    def _add_helper_segments(self):
        delay_time = self._rf_parameters["delay_time"]
        
        break_time = 10 * ureg.us
        segment = SegmentEmpty("break", break_time)
        self.add_segment(segment)

        segment = Segment("field_plate_break", break_time)
        if self._field_plate_parameters["use"]:
            field_plate = AWGConstant(self._field_plate_parameters["amplitude"])
            field_plate_channel = get_channel_from_name(self._field_plate_parameters["name"])
            segment.add_awg_function(field_plate_channel, field_plate)
        self.add_segment(segment)
        self._field_plate_repeats = int(
            self._field_plate_parameters["padding_time"] / break_time
        )
        
        # piov2 <-> pi pulse delay
        segment = SegmentEmpty("delay", delay_time)
        self.add_segment(segment)

    def setup_sequence(self):
        detect_chasm_repeats = self._detect_parameters["chasm_repeats"]
        detect_antihole_repeats = self._detect_parameters["antihole_repeats"]
        detect_rf_repeats = self._detect_parameters["rf_repeats"]

        antihole_repeats_one_frequency = 1

        segment_repeats = []

        segment_repeats.append(("chasm", self._chasm_repeats))
        segment_repeats.append(("break", 1))
        segment_repeats.append(("detect", detect_chasm_repeats))

        segment_repeats.append(
            ("field_plate_break", self._field_plate_repeats)
        )  # waiting for the field plate to go high
        for kk in range(self._antihole_segments_and_repeats[0][1] // antihole_repeats_one_frequency):
            for segment, repeats in self._antihole_segments_and_repeats:
                segment_repeats.append((segment.name, antihole_repeats_one_frequency))
        segment_repeats.append(
            ("break", self._field_plate_repeats)
        )  # waiting for the field plate to go low
        segment_repeats.append(("detect", detect_antihole_repeats))

        segment_repeats.append(("piov2_pulse", 1))
        segment_repeats.append(("delay", 1))
        segment_repeats.append(("pi_pulse", 1))
        segment_repeats.append(("delay", 1))
        segment_repeats.append(("piov2_pulse", 1))

        segment_repeats.append(("break", 1))
        segment_repeats.append(("detect", detect_rf_repeats))
        return super().setup_sequence(segment_repeats)

    def num_of_records(self) -> int:
        return (
            self._detect_parameters["chasm_repeats"]
            + self._detect_parameters["antihole_repeats"]
            + self._detect_parameters["rf_repeats"]
        )

