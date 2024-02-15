import numbers
from typing import Any, Union, Optional

import numpy as np

from onix.models.hyperfine import energies
from onix.sequences.sequence import (
    AWGConstant,
    AWGFunction,
    AWGSineTrain,
    AWGSinePulse,
    AWGSineSweep,
    Segment,
    SegmentEmpty,
    Sequence,
)
from onix.sequences.shared import antihole_segment, chasm_segment, detect_segment, rf_assist_segment
from onix.units import ureg, Q_
from onix.awg_maps import get_channel_from_name


class AWGSineSweepNoise(AWGSineSweep):
    def __init__(
        self,
        start_frequency: Union[float, Q_],
        stop_frequency: Union[float, Q_],
        amplitude: float,
        start_time: Optional[Union[float, Q_]],
        end_time: Optional[Union[float, Q_]],
        phase: float = 0,
        phase_noise: float = 0,
    ):
        super().__init__(start_frequency, stop_frequency, amplitude, start_time, end_time, phase)
        self._phase_noise = phase_noise

    def output(self, times):
        phases = np.cumsum(np.random.normal(0, self._phase_noise, size=len(times))) + self._phase
        start_frequency = self._start_frequency.to("Hz").magnitude
        stop_frequency = self._stop_frequency.to("Hz").magnitude
        start_time = self._start_time.to("s").magnitude
        end_time = self._end_time.to("s").magnitude
        duration = end_time - start_time
        frequency_scan = stop_frequency - start_frequency
        instant_frequencies = (
            times - start_time
        ) / duration * frequency_scan / 2 + start_frequency
        sine_sweep = self._amplitude * np.sin(
            2 * np.pi * instant_frequencies * times + phases
        )
        mask_start = np.heaviside(times - start_time, 0)
        mask_end = np.heaviside(end_time - times, 1)
        return sine_sweep * mask_start * mask_end

    @property
    def min_duration(self) -> Q_:
        return self._end_time

    @property
    def max_amplitude(self):
        return self._amplitude


class RFSatAbsSpectroscopy(Sequence):
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
        params = self._chasm_parameters.copy()
        params["transition"] = "ac"
        segment, self._chasm_repeats = chasm_segment(
            "chasm_ac",
            self._ao_parameters,
            self._eos_parameters,
            self._field_plate_parameters,
            params,
        )
        self.add_segment(segment)
        params = self._chasm_parameters.copy()
        params["transition"] = "ca"
        segment, self._chasm_repeats = chasm_segment(
            "chasm_ca",
            self._ao_parameters,
            self._eos_parameters,
            self._field_plate_parameters,
            params,
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
        segment = rf_assist_segment(
            "rf_assist",
            self._antihole_parameters["rf_assist"],
            self._field_plate_parameters,
        )
        self.add_segment(segment)
        params = self._antihole_parameters["rf_assist"].copy()
        params["offset_start"] = -110 * ureg.kHz
        params["offset_end"] = 170 * ureg.kHz
        # params["amplitude"] = 0
        params1 = self._field_plate_parameters.copy()
        params1["use"] = False
        segment = rf_assist_segment(
            "rf_assist1",
            params,
            params1,
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

    def _add_rf_segment(self):
        lower_state = self._rf_parameters["transition"][0]
        upper_state = self._rf_parameters["transition"][1]
        frequency_1 = (
            energies["7F0"][upper_state]
            - energies["7F0"][lower_state]
            + self._rf_parameters["offset_1"]
            + self._rf_parameters["detuning_1"]
        )
        frequency_2 = (
            energies["7F0"][upper_state]
            - energies["7F0"][lower_state]
            + self._rf_parameters["offset_2"]
            + self._rf_parameters["detuning_2"]
        )
        pulse_1_time = self._rf_parameters["pulse_1_time"]
        delay_time = self._rf_parameters["delay_time"]
        segment = Segment("rf_1", pulse_1_time + delay_time)
        # if self._rf_parameters["simultaneous_driving"]:
        #     rf_pulse = AWGSimultaneousTwoFrequencies(
        #         pulse_time,
        #         frequency_1,
        #         frequency_2,
        #         self._rf_parameters["amplitude_1"],
        #         self._rf_parameters["amplitude_2"],
        #     )
        # else:
        #     rf_pulse = AWGSineSweep(
        #         frequency_1.to("Hz").magnitude,
        #         frequency_2.to("Hz").magnitude,
        #         self._rf_parameters["amplitude"],
        #         0,
        #         self._rf_parameters["pulse_time"],
        #     )
        rf_pulse = AWGSineSweep(
                frequency_1 - self._rf_parameters["frequency_1_span"],
                frequency_1 + self._rf_parameters["frequency_1_span"],
                self._rf_parameters["amplitude_1"],
                0,
                self._rf_parameters["pulse_1_time"],
            )
        rf_channel = get_channel_from_name(self._rf_parameters["name"])
        segment.add_awg_function(rf_channel, rf_pulse)
        self.add_segment(segment)

        segment = Segment("rf_2")
        rf_pulse = AWGSineSweepNoise(
            frequency_2 - self._rf_parameters["frequency_2_span"],
            frequency_2 + self._rf_parameters["frequency_2_span"],
            self._rf_parameters["amplitude_2"],
            0,
            self._rf_parameters["pulse_2_time"],
            0,
            self._rf_parameters["phase_noise"],
        )
        rf_channel = get_channel_from_name(self._rf_parameters["name"])
        segment.add_awg_function(rf_channel, rf_pulse)
        self.add_segment(segment)


    def _add_helper_segments(self):
        break_time = 10 * ureg.us
        segment = SegmentEmpty("break", break_time)
        self.add_segment(segment)
        break_time = 10 * ureg.ms
        segment = SegmentEmpty("long_break", break_time)
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

    def setup_sequence(self):
        detect_chasm_repeats = self._detect_parameters["chasm_repeats"]
        detect_antihole_repeats = self._detect_parameters["antihole_repeats"]
        detect_rf_repeats = self._detect_parameters["rf_repeats"]

        segment_repeats = []


        for kk in range(self._chasm_repeats):
            segment_repeats.append(("chasm", 1))
            segment_repeats.append(("rf_assist1", 1))
        segment_repeats.append(("break", 1))
        segment_repeats.append(("long_break", 5))
        segment_repeats.append(("detect", detect_chasm_repeats))

        segment_repeats.append(
            ("field_plate_break", self._field_plate_repeats)
        )  # waiting for the field plate to go high
        for kk in range(self._antihole_segments_and_repeats[0][1]):
            if self._antihole_parameters["rf_assist"]["use_sequential"]:
                segment_repeats.append(("rf_assist", 1))
            for segment, repeats in self._antihole_segments_and_repeats:
                segment_repeats.append((segment.name, 1))
        segment_repeats.append(
            ("break", self._field_plate_repeats)
        )  # waiting for the field plate to go low
        segment_repeats.append(("long_break", 5))
        segment_repeats.append(("detect", detect_antihole_repeats))

        segment_repeats.append(("rf_1", 1))
        segment_repeats.append(("rf_2", 1))
        segment_repeats.append(("break", 1))
        segment_repeats.append(("detect", detect_rf_repeats))
        return super().setup_sequence(segment_repeats)

    def num_of_records(self) -> int:
        return (
            self._detect_parameters["chasm_repeats"]
            + self._detect_parameters["antihole_repeats"]
            + self._detect_parameters["rf_repeats"]
        )

