from typing import Any, List, Tuple
import warnings

import numpy as np
from onix.models.hyperfine import energies
from onix.sequences.sequence import (
    AWGSinePulse,
    AWGConstant,
    AWGSineSweep,
    AWGSineTrain,
    MultiSegments,
    Segment,
    SegmentEmpty,
    Sequence,
    TTLPulses,
)
from onix.units import Q_, ureg

PIECEWISE_TIME = 10 * ureg.ms


def chasm_segment(
    name: str,
    ao_parameters: dict[str, Any],
    eos_parameters: dict[str, Any],
    field_plate_parameters: dict[str, Any],
    chasm_parameters: dict[str, Any],
    reverse_stark_order: bool = False,
):
    transition = chasm_parameters["transition"]
    scan = chasm_parameters["scan"]
    scan_rate = chasm_parameters["scan_rate"]
    detuning = chasm_parameters["detuning"]
    duration = scan / scan_rate
    if not field_plate_parameters["use"]:
        return _scan_segment(
            name,
            ao_parameters,
            eos_parameters,
            transition,
            duration,
            scan,
            detuning,
        )
    else:
        if reverse_stark_order:
            polarities = [1, -1]
        else:
            polarities = [-1, 1]
        segment_repeats = [
            _scan_segment(
                name,
                ao_parameters,
                eos_parameters,
                transition,
                duration,
                scan,
                detuning + field_plate_parameters["stark_shift"] * polarity,
            )
            for polarity in polarities
        ]
        segment = MultiSegments(
            name, [segment for (segment, repeats) in segment_repeats]
        )
        return (segment, segment_repeats[0][1])


def antihole_segment(
    name: str,
    ao_parameters: dict[str, Any],
    eos_parameters: dict[str, Any],
    field_plate_parameters: dict[str, Any],
    antihole_parameters: dict[str, Any],
    reverse_transition_order: bool = False,
):
    transitions: list[str] = antihole_parameters["transitions"]
    if reverse_transition_order:
        transitions.reverse()
    scan = antihole_parameters["scan"]
    scan_rate = antihole_parameters["scan_rate"]
    detuning = antihole_parameters["detuning"]
    duration = scan / scan_rate
    segment_repeats = [
        _scan_segment(
            name,
            ao_parameters,
            eos_parameters,
            transition,
            duration,
            scan,
            detuning,
        )
        for transition in transitions
    ]
    if field_plate_parameters["use"]:
        for segment, repeats in segment_repeats:
            field_plate = AWGConstant(field_plate_parameters["amplitude"])
            segment.add_awg_function(field_plate_parameters["channel"], field_plate)
    segment = MultiSegments(name, [segment for (segment, repeats) in segment_repeats])

    return (segment, segment_repeats[0][1])


def detect_segment(
    name: str,
    ao_parameters: dict[str, Any],
    eos_parameters: dict[str, Any],
    field_plate_parameters: dict[str, Any],
    detect_parameters: dict[str, Any],
):
    segment = Segment(name)
    ttl_start_time = 0 * ureg.us  # digitizer trigger pulse start time.
    ttl_duration = 4 * ureg.us  # digitizer trigger pulse duration
    ttl_stop_time = ttl_start_time + ttl_duration
    detect_padding_time = 4 * ureg.us  # extra data recording time around the detection
    ttl_function = TTLPulses([[ttl_start_time, ttl_stop_time]])
    segment.add_ttl_function(detect_parameters["trigger_channel"], ttl_function)

    transition = detect_parameters["transition"]
    eo_parameters = eos_parameters[transition]
    if transition is not None:
        F_state = transition[0]
        D_state = transition[1]
        frequency = (
            energies["5D0"][D_state]
            - energies["7F0"][F_state]
            + eo_parameters["offset"]
        )
    print(name, round(frequency, 2))

    detect_detunings = detect_parameters["detunings"]
    if field_plate_parameters["use"]:
        all_detunings = np.empty(
            (detect_detunings.size * 2,), dtype=detect_detunings.dtype
        )
        all_detunings *= detect_detunings.units
        all_detunings[0::2] = detect_detunings - field_plate_parameters["stark_shift"]
        all_detunings[1::2] = detect_detunings + field_plate_parameters["stark_shift"]
        detect_detunings = all_detunings
    if detect_parameters["randomize"]:
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=UserWarning)
            np.random.shuffle(detect_detunings)

    start_time = ttl_start_time + detect_padding_time
    on_time = detect_parameters["on_time"]
    off_time = detect_parameters["off_time"]
    eo_amplitude = eo_parameters["amplitude"]
    eo_pulse = AWGSinePulse(frequency, eo_amplitude)
    eo_channel = get_channel_from_name(eo_parameters["name"])
    segment.add_awg_function(eo_channel, eo_pulse)

    ao_frequencies = (
        ao_parameters["frequency"] + detect_detunings / ao_parameters["order"]
    )
    ao_pulse = AWGSineTrain(
        on_time,
        off_time,
        ao_frequencies,
        ao_parameters["detect_amplitude"],
        start_time=start_time + off_time / 2,
    )
    segment.add_awg_function(ao_parameters["channel"], ao_pulse)

    detect_pulse_times = [
        (
            detect_padding_time + off_time / 2 + kk * (on_time + off_time),
            detect_padding_time + off_time / 2 + on_time + kk * (on_time + off_time),
        )
        for kk in range(len(detect_detunings))
    ]
    detect_pulse_times = [
        (
            (pulse_start + ao_parameters["rise_delay"]).to("s").magnitude,
            (pulse_end + ao_parameters["fall_delay"]).to("s").magnitude,
        )
        for (pulse_start, pulse_end) in detect_pulse_times
    ]
    analysis_parameters = {
        "detect_detunings": detect_detunings,
        "digitizer_duration": segment.duration - ttl_start_time,
        "detect_pulse_times": detect_pulse_times,
    }
    segment._duration = segment.duration + 4 * ureg.us  # make sure that the digitizer can trigger again
    return (segment, analysis_parameters)


def _scan_segment(
    name: str,
    ao_parameters: dict[str, Any],
    eos_parameters: dict[str, Any],
    transition: str,
    duration: Q_,
    scan: Q_,
    detuning: Q_ = 0 * ureg.Hz,
):
    eo_parameters = eos_parameters[transition]
    repeats = 1
    if duration > PIECEWISE_TIME:
        repeats = int(duration / PIECEWISE_TIME) + 1
        duration = duration / repeats
    F_state = transition[0]
    D_state = transition[1]
    frequency = (
        energies["5D0"][D_state] - energies["7F0"][F_state] + eo_parameters["offset"]
    )
    print(name, round(frequency, 2))
    segment = Segment(name, duration)
    start = ao_parameters["frequency"] + (detuning - scan) / ao_parameters["order"]
    end = ao_parameters["frequency"] + (detuning + scan) / ao_parameters["order"]
    ao_pulse = AWGSineSweep(start, end, ao_parameters["amplitude"], 0, duration)
    segment.add_awg_function(ao_parameters["channel"], ao_pulse)
    eo_pulse = AWGSinePulse(frequency, eo_parameters["amplitude"])
    eo_channel = get_channel_from_name(eo_parameters["name"])
    segment.add_awg_function(eo_channel, eo_pulse)
    return (segment, repeats)


class SharedSequence(Sequence):
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
        self._add_chasm()
        self._add_antihole()
        self._add_detect()
        self._add_breaks()

    def _add_chasm(self):  # TODO: combine multiple chasm segments
        segment, self._chasm_repeats = chasm_segment(
            "chasm",
            self._ao_parameters,
            self._eos_parameters,
            self._field_plate_parameters,
            self._chasm_parameters,
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

    def _add_antihole(self):
        segment, self._antihole_repeats = antihole_segment(
            "antihole",
            self._ao_parameters,
            self._eos_parameters,
            self._field_plate_parameters,
            self._antihole_parameters,
            return_separate_segments=True,
        )
        self.add_segment(segment)

    def _add_detect(self):
        segment, self.analysis_parameters = detect_segment(
            "detect",
            self._ao_parameters,
            self._eos_parameters,
            self._field_plate_parameters,
            self._detect_parameters,
        )
        self.analysis_parameters["detect_groups"] = []
        self.add_segment(segment)

    def _add_breaks(self):
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

    def define_chasm(self):
        segment_steps = []
        segment_steps.append(("chasm", self._chasm_repeats))
        segment_steps.append(("long_break", 5))  # TODO: replace with shutter.
        detect_cycles = self._detect_parameters["cycles"]["chasm"]
        segment_steps.append(("detect", detect_cycles))
        self.analysis_parameters["detect_groups"].append(("chasm", detect_cycles))
        return segment_steps

    def define_antihole(self):
        segment_steps = []
        # waiting for the field plate to go high
        segment_steps.append(("field_plate_break", self._field_plate_repeats))
        segment_steps.append(("antihole", self._antihole_repeats))
        # waiting for the field plate to go low
        segment_steps.append(("break", self._field_plate_repeats))
        segment_steps.append(("long_break", 5))  # TODO: replace with shutter.
        detect_cycles = self._detect_parameters["cycles"]["antihole"]
        segment_steps.append(("detect", detect_cycles))
        self.analysis_parameters["detect_groups"].append(("antihole", detect_cycles))
        return segment_steps

    def define_after_antihole(self):
        """This must be defined in derived classes."""
        raise NotImplementedError()

    def setup_sequence(self):
        segment_steps = []
        segment_steps.extend(self.define_chasm())
        segment_steps.extend(self.define_antihole())
        segment_steps.extend(self.define_after_antihole())
        return super().setup_sequence(segment_steps)
