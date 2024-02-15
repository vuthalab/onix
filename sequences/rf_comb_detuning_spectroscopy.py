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


class RFPumpAndProbe(AWGFunction):
    def __init__(
        self,
        pump_frequency,
        pump_amplitude,
        pump_time,
        delay_time,
        probe_frequency,
        probe_amplitude,
        probe_time,
        probe_phase,
    ):
        self._pump_frequency = pump_frequency.to("Hz").magnitude
        self._pump_amplitude = pump_amplitude
        self._pump_time = pump_time.to("s").magnitude
        self._delay_time = delay_time.to("s").magnitude
        self._probe_frequency = probe_frequency.to("Hz").magnitude
        self._probe_amplitude = probe_amplitude
        self._probe_time = probe_time.to("s").magnitude
        self._probe_phase = probe_phase


    def output(self, times):
        def sine(times, frequency, amplitude, phase, start_time, end_time):
            mask = np.heaviside(times - start_time, 1) - np.heaviside(times - end_time, 1)
            return mask * amplitude * np.sin(2 * np.pi * frequency * times + phase)

        data = np.zeros(len(times))
        start_time = 0
        end_time = start_time + self._pump_time
        data += sine(times, self._pump_frequency, self._pump_amplitude, 0, start_time, end_time)
        start_time = end_time + self._delay_time
        end_time = start_time + self._probe_time
        data += sine(times, self._probe_frequency, self._probe_amplitude, self._probe_phase, start_time, end_time)
        return data

    @property
    def max_amplitude(self) -> float:
        return np.max([self._pump_amplitude, self._probe_amplitude])

    @property
    def min_duration(self) -> Q_:
        time = self._pump_time + self._delay_time + self._probe_time + self._delay_time
        return time * ureg.s

class RFCombDetuningSpectroscopy(Sequence):
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
            "chasm_bb",
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
        #self.add_segment(segment)
        params = self._chasm_parameters.copy()
        params["transition"] = "ca"
        segment, self._chasm_repeats = chasm_segment(
            "chasm_ca",
            self._ao_parameters,
            self._eos_parameters,
            self._field_plate_parameters,
            params,
        )
        #self.add_segment(segment)

        segment, self._antihole_repeats = antihole_segment(
            "antihole",
            self._ao_parameters,
            self._eos_parameters,
            self._field_plate_parameters,
            self._antihole_parameters,
            return_separate_segments=False,
        )
        self.add_segment(segment)


        segment = rf_assist_segment(
            "rf_assist",
            self._antihole_parameters["rf_assist"],
            self._field_plate_parameters,
        )
        if self._field_plate_parameters["use"]:
            field_plate = AWGConstant(self._field_plate_parameters["amplitude"])
            field_plate_channel = get_channel_from_name(self._field_plate_parameters["name"])
            segment.add_awg_function(field_plate_channel, field_plate)
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
        transition_center = energies["7F0"][upper_state] - energies["7F0"][lower_state]

        pump_offsets = self._rf_parameters["pump_offsets"]
        pump_freqs = transition_center + pump_offsets
        pump_time = self._rf_parameters["pump_time"]
        pump_amplitude = self._rf_parameters["pump_amplitude"]

        probe_offset = self._rf_parameters["probe_offset"]
        probe_time = self._rf_parameters["probe_time"]
        probe_amplitude = self._rf_parameters["probe_amplitude"]
        probe_phase = self._rf_parameters["probe_phase"]

        delay_time = self._rf_parameters["delay_time"]
        rf_channel = get_channel_from_name(self._rf_parameters["name"])

        for kk in range(len(pump_offsets)):
            segment = Segment(f"rf_{kk}")
            segment.add_awg_function(
                rf_channel,
                RFPumpAndProbe(
                    pump_freqs[kk],
                    pump_amplitude,
                    pump_time,
                    delay_time,
                    pump_freqs[kk] + probe_offset,
                    probe_amplitude,
                    probe_time,
                    probe_phase,
                )
            )
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
            segment_repeats.append(("chasm_bb", 1))
            segment_repeats.append(("rf_assist1", 1))
        segment_repeats.append(("break", 1))
        segment_repeats.append(("long_break", 5))
        segment_repeats.append(("detect", detect_chasm_repeats))

        segment_repeats.append(
            ("field_plate_break", self._field_plate_repeats)
        )  # waiting for the field plate to go high
        for kk in range(self._antihole_repeats):
            if self._antihole_parameters["rf_assist"]["use_sequential"]:
                segment_repeats.append(("rf_assist", 1))
            segment_repeats.append(("antihole", self._antihole_repeats))
        segment_repeats.append(
            ("break", self._field_plate_repeats)
        )  # waiting for the field plate to go low
        segment_repeats.append(("long_break", 5))
        segment_repeats.append(("detect", detect_antihole_repeats))

        for kk in range(len(self._rf_parameters["pump_offsets"])):
            segment_repeats.append((f"rf_{kk}", 1))
        segment_repeats.append(("break", 1))
        segment_repeats.append(("detect", detect_rf_repeats))
        return super().setup_sequence(segment_repeats)

    def num_of_records(self) -> int:
        return (
            self._detect_parameters["chasm_repeats"]
            + self._detect_parameters["antihole_repeats"]
            + self._detect_parameters["rf_repeats"]
        )
