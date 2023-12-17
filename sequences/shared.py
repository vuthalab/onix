from typing import Any
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
    TTLPulses,
)
from onix.units import Q_, ureg
from onix.awg_maps import get_channel_from_name

PIECEWISE_TIME = 20 * ureg.ms


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
    duration = scan * 2 / scan_rate
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
    return_separate_segments: bool = False,
):
    transitions: list[str] = antihole_parameters["transitions"]
    if reverse_transition_order:
        transitions.reverse()
    scan = antihole_parameters["scan"]
    scan_rate = antihole_parameters["scan_rate"]
    detuning = antihole_parameters["detuning"]
    if scan.to("Hz").magnitude == 0:
        duration = antihole_parameters["duration_no_scan"]
    else:
        duration = scan / scan_rate
    segment_repeats = [
        _scan_segment(
            name + "_" + transition,
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
            field_plate_channel = get_channel_from_name(field_plate_parameters["name"])
            segment.add_awg_function(field_plate_channel, field_plate)

    if not return_separate_segments:
        segment = MultiSegments(name, [segment for (segment, repeats) in segment_repeats])
        return (segment, segment_repeats[0][1])
    else:
        return segment_repeats


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
    print(name, transition, round(frequency, 2))

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
    end_time = (
        start_time + (on_time + off_time) * len(detect_detunings) + detect_padding_time
    )
    eo_amplitude = eo_parameters["amplitude"]
    eo_pulse = AWGSinePulse(
        frequency, eo_amplitude, start_time=start_time, end_time=end_time
    )
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
    ao_channel = get_channel_from_name(ao_parameters["name"])
    segment.add_awg_function(ao_channel, ao_pulse)

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
        energies["5D0"][D_state] - energies["7F0"][F_state] + eo_parameters["offset"] + detuning
    )
    print(name, transition, round(frequency, 2))
    segment = Segment(name, duration)
    start = ao_parameters["frequency"] - scan / ao_parameters["order"]
    end = ao_parameters["frequency"] + scan / ao_parameters["order"]
    ao_pulse = AWGSineSweep(start, end, ao_parameters["amplitude"], 0, duration)
    #print("ao", start, end, ao_parameters["amplitude"], 0, duration)
    ao_channel = get_channel_from_name(ao_parameters["name"])
    segment.add_awg_function(ao_channel, ao_pulse)
    eo_pulse = AWGSinePulse(frequency, eo_parameters["amplitude"])
    #print("eo", frequency, eo_parameters["amplitude"])
    eo_channel = get_channel_from_name(eo_parameters["name"])
    segment.add_awg_function(eo_channel, eo_pulse)
    return (segment, repeats)
