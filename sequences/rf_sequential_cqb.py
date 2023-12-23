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


class AWGSEQCQB(AWGFunction):
    def __init__(
        self,
        piov2_time: Union[float, Q_],
        pi_time: Union[float, Q_],
        delay_time_1: Union[float, Q_],
        delay_time_2: Union[float, Q_],
        delay_time_3: Union[float, Q_],
        frequency_1: Union[float, Q_],
        frequency_2: Union[float, Q_],
        amplitude_1: float,
        amplitude_2: float,
    ):
        super().__init__()
        self._piov2_time = piov2_time
        self._pi_time = pi_time
        self._delay_time_1 = delay_time_1
        self._delay_time_2 = delay_time_2
        self._delay_time_3 = delay_time_3
        self._frequency_1 = frequency_1
        self._frequency_2 = frequency_2
        self._amplitude_1 = amplitude_1
        self._amplitude_2 = amplitude_2

    def output(self, times):
        def sine_rect(times, t0, T, freq):
            # return np.heaviside(times + T/2 + t0, 1) - np.heaviside(times - T/2 - t0, 1)
            return (np.heaviside(times - t0, 1) - np.heaviside(times - t0 - T, 1)) * np.exp(1j*times*freq)
        
        def four_pulse_train(times):
            frequency_1 = self._frequency_1.to("Hz").magnitude
            frequency_2 = self._frequency_2.to("Hz").magnitude

            piov2_time = self._piov2_time.to("s").magnitude
            pi_time = self._pi_time.to("s").magnitude
            delay_time_1 = self._delay_time_1.to("s").magnitude
            delay_time_2 = self._delay_time_2.to("s").magnitude
            delay_time_3 = self._delay_time_3.to("s").magnitude
            
            t0 = 0
            t1 = t0 + piov2_time + delay_time_1
            t2 = t1 + pi_time + delay_time_2
            t3 = t2 + pi_time + delay_time_3

            T0 = piov2_time
            T1 = pi_time
            T2 = pi_time
            T3 = piov2_time

            f0 = frequency_1
            f1 = frequency_2
            f2 = frequency_2
            f3 = frequency_1

            amplitude_1 = self._amplitude_1
            amplitude_2 = self._amplitude_2

            return np.real(amplitude_1*sine_rect(times, t0, T0, f0) + 
                           amplitude_2*sine_rect(times, t1, T1, f1) + 
                           np.exp(1j*np.pi) * (amplitude_2*sine_rect(times, t2, T2, f2) + 
                                               amplitude_1*sine_rect(times, t3, T3, f3)))

        return four_pulse_train(times)
    
    @property
    def min_duration(self) -> Q_:
        return self._delay_time_1 + self._delay_time_2 + self._delay_time_3 + 2*self._pi_time + 2*self._piov2_time

    @property
    def max_amplitude(self):
        return np.max([self._amplitude_1, self._amplitude_2])


class RFSEQCQB(Sequence):
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
        # pulse_time = self._rf_parameters["pulse_time"]
        # delay_time = self._rf_parameters["delay_time"]
        segment = Segment("rf")
        rf_pulse = AWGSEQCQB(
            self._rf_parameters["piov2_time"],
            self._rf_parameters["pi_time"],
            self._rf_parameters["delay_time_1"],
            self._rf_parameters["delay_time_2"],
            self._rf_parameters["delay_time_3"],
            frequency_1,
            frequency_2,
            self._rf_parameters["amplitude_1"],
            self._rf_parameters["amplitude_2"]
        )
        rf_channel = get_channel_from_name(self._rf_parameters["name"])
        segment.add_awg_function(rf_channel, rf_pulse)
        self.add_segment(segment)

    def _add_helper_segments(self):
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

        segment_repeats.append(("rf", 1))
        segment_repeats.append(("break", 1))
        segment_repeats.append(("detect", detect_rf_repeats))
        return super().setup_sequence(segment_repeats)

    def num_of_records(self) -> int:
        return (
            self._detect_parameters["chasm_repeats"]
            + self._detect_parameters["antihole_repeats"]
            + self._detect_parameters["rf_repeats"]
        )

