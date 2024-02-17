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
from onix.sequences.shared import antihole_segment, chasm_segment, detect_segment, rf_assist_segment
from onix.units import ureg, Q_
from onix.awg_maps import get_channel_from_name


class AWGSEQCQB(AWGFunction):
    def __init__(
        self,
        piov2_time: Union[float, Q_],
        piov2_frequency: Union[float, Q_],
        piov2_amplitude: float,
        piov2_phase_shift: float,
        pi_time: Union[float, Q_],
        pi_start_frequency: Union[float, Q_],
        pi_stop_frequency: Union[float, Q_],
        pi_amplitude: float,
        pi_phase_shift: float,
        pi_reverse_frequency: bool,
        delay_time_piov2_pi: Union[float, Q_],
        delay_time: Union[float, Q_],
    ):
        super().__init__()
        self._piov2_time = piov2_time
        self._piov2_frequency = piov2_frequency
        self._piov2_amplitude = piov2_amplitude
        self._piov2_phase_shift = piov2_phase_shift

        self._pi_time = pi_time
        self._pi_start_frequency = pi_start_frequency
        self._pi_stop_frequency = pi_stop_frequency
        self._pi_amplitude = pi_amplitude
        self._pi_phase_shift = pi_phase_shift
        self._pi_reverse_frequency = pi_reverse_frequency

        self._delay_time_piov2_pi = delay_time_piov2_pi
        self._delay_time = delay_time

    def output(self, times):
        def sine_rect(times, t0, T, freq, phase):
            return (np.heaviside(times - t0, 1) - np.heaviside(times - (t0 + T), 1)) * np.exp(1j * (2 * np.pi * freq * times + phase))
        
        def sine_sweep_rect(times, t0, T, freq_start, freq_stop, phase):
            frequency_scan = freq_stop - freq_start
            instant_frequencies = (times - t0) / T * frequency_scan / 2 + freq_start
            return (np.heaviside(times - t0, 1) - np.heaviside(times - (t0 + T), 1)) * np.exp(1j * (2 * np.pi * instant_frequencies * times  + phase))

        def four_pulse_train(times):
            piov2_freq = self._piov2_frequency.to("Hz").magnitude
            pi_start_freq = self._pi_start_frequency.to("Hz").magnitude
            pi_stop_freq = self._pi_stop_frequency.to("Hz").magnitude

            piov2_time = self._piov2_time.to("s").magnitude
            pi_time = self._pi_time.to("s").magnitude
            delay_time_piov2_pi = self._delay_time_piov2_pi.to("s").magnitude
            delay_time = self._delay_time.to("s").magnitude

            t0 = 0
            t1 = t0 + piov2_time + delay_time_piov2_pi
            t2 = t1 + pi_time + delay_time
            t3 = t2 + pi_time + delay_time_piov2_pi

            piov2_pulses = self._piov2_amplitude * (
                sine_rect(times, t0, piov2_time, piov2_freq, 0)
                + sine_rect(times, t3, piov2_time, piov2_freq, self._piov2_phase_shift)
            )
            if self._pi_reverse_frequency:
                second_pi_start_freq = pi_stop_freq
                second_pi_stop_freq = pi_start_freq
            else:
                second_pi_start_freq = pi_start_freq
                second_pi_stop_freq = pi_stop_freq
            pi_pulses = self._pi_amplitude * (
                sine_sweep_rect(times, t1, pi_time, pi_start_freq, pi_stop_freq, 0)
                + sine_sweep_rect(times, t2, pi_time, second_pi_start_freq, second_pi_stop_freq, self._pi_phase_shift)
            )
            return np.real(piov2_pulses + pi_pulses)

        return four_pulse_train(times)
    
    @property
    def min_duration(self) -> Q_:
        return (
            self._piov2_time * 2
            + self._delay_time_piov2_pi * 2
            + self._pi_time * 2
            + self._delay_time
         )

    @property
    def max_amplitude(self):
        return np.max([self._piov2_amplitude, self._pi_amplitude])


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
        segment = rf_assist_segment(
            "rf_assist",
            self._antihole_parameters["rf_assist"]
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
        freq_no_offset = energies["7F0"][upper_state] - energies["7F0"][lower_state]
        segment = Segment("rf")
        rf_pulse = AWGSEQCQB(
            self._rf_parameters["piov2_time"],
            self._rf_parameters["piov2_offset"] + freq_no_offset,
            self._rf_parameters["piov2_amplitude"],
            self._rf_parameters["piov2_phase_shift"],
            self._rf_parameters["pi_time"],
            self._rf_parameters["pi_start_offset"] + freq_no_offset,
            self._rf_parameters["pi_stop_offset"] + freq_no_offset,
            self._rf_parameters["pi_amplitude"],
            self._rf_parameters["pi_phase_shift"],
            self._rf_parameters["pi_reverse_frequency"],
            self._rf_parameters["delay_time_piov2_pi"],
            self._rf_parameters["delay_time"],
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

        segment_repeats = []

        segment_repeats.append(("chasm", self._chasm_repeats))
        segment_repeats.append(("break", 1))
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

