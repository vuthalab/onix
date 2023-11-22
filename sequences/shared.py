from typing import Dict, List, Union

from onix.models.hyperfine import energies
from onix.units import Q_, ureg
from onix.sequences.sequence import (
    Segment,
    MultiSegments,
    AWGSinePulse,
    AWGSineSweep,
    AWGSineTrain,
    TTLOff,
    TTLOn,
    TTLPulses,
)

PIECEWISE_TIME = 10 * ureg.ms


def chasm_segment(
    name: str,
    ao_parameters: Dict,
    eo_parameters: Dict,
    field_plate_parameters: Dict,
    chasm_parameters: Dict,
    transition: str,
    scan: Q_,
    scan_rate: Q_,
    detuning: Q_ = 0 * ureg.Hz,
):
    transition = chasm_parameters["transition"]
    duration = scan / scan_rate
    if not field_plate_parameters["use"]:
        return scan_segment(
            name,
            ao_parameters,
            eo_parameters,
            transition,
            duration,
            scan,
            detuning,
        )
    else:
        segment_repeats = [
            scan_segment(
                name,
                ao_parameters,
                eo_parameters,
                transition,
                duration,
                scan,
                detuning + field_plate_parameters["stark_shift"] * polarity,
            ) for polarity in [-1, 1]
        ]
        segment = MultiSegments(name, [segment for (segment, repeats) in segment_repeats])
        return (segment, segment_repeats[0][1])


def antihole_segment(
    name: str,
    ao_parameters: Dict,
    eo_parameters: Dict,
    transitions: List[str],
    duration: Q_,
    detuning: Q_ = 0 * ureg.Hz,
):
    segment_repeats = [
        scan_segment(
            name,
            ao_parameters,
            eo_parameters,
            transition,
            duration,
            0 * ureg.Hz,
            detuning,
        ) for transition in transitions
    ]
    segment = MultiSegments(name, [segment for (segment, repeats) in segment_repeats])
    return (segment, segment_repeats[0][1])


def scan_segment(
    name: str,
    ao_parameters: Dict,
    eo_parameters: Dict,
    transition: Union[str, None],
    duration: Q_,
    scan: Q_,
    detuning: Q_ = 0 * ureg.Hz,
):
    repeats = 1
    if duration > PIECEWISE_TIME:
        repeats = int(duration / PIECEWISE_TIME) + 1
        duration = PIECEWISE_TIME
    if transition is not None:
        F_state = transition[0]
        D_state = transition[1]
        frequency = energies["5D0"][D_state] - energies["7F0"][F_state] + eo_parameters["offset"] + detuning
    else:
        frequency = detuning
    print(name, round(frequency, 2))
    segment = Segment(name, duration)
    lower = (frequency - scan) / eo_parameters["order"]
    upper = (frequency + scan) / eo_parameters["order"]
    ao_pulse = AWGSinePulse(ao_parameters["frequency"], ao_parameters["amplitude"])
    segment.add_awg_function(ao_parameters["channel"], ao_pulse)
    eo_pulse = AWGSineSweep(lower, upper, eo_parameters["amplitude"], 0, duration)
    segment.add_awg_function(eo_parameters["channel"], eo_pulse)
    return (segment, repeats)


def detect_segment(
    name: str,
    ao_parameters: Dict,
    eo_parameters: Dict,
    detect_ao_parameters: Dict,
    field_plate_parameters: Dict,
    digitizer_channel: int,
    transition: str,
    detect_detunings: Q_,
    on_time: Q_,
    off_time: Q_,
    ttl_detect_offset_time: Q_ = 4 * ureg.us,
    ttl_start_time: Q_ = 12 * ureg.us,
    ttl_duration: Q_ = 4 * ureg.us,
):
    if transition is not None:
        F_state = transition[0]
        D_state = transition[1]
        frequency = energies["5D0"][D_state] - energies["7F0"][F_state] + eo_parameters["offset"]
    else:
        frequency = eo_parameters["offset"]
    print(name, round(frequency, 2))
    detect_frequencies = detect_detunings + frequency
    eo_amplitude = eo_parameters["amplitude"]

    segment = Segment(name)
    ttl_stop_time = ttl_start_time + ttl_duration
    ttl_function = TTLPulses([[ttl_start_time, ttl_stop_time]])
    segment.add_ttl_function(digitizer_channel, ttl_function)
    start_time = ttl_start_time + ttl_detect_offset_time
    eo_pulse = AWGSineTrain(
        on_time + off_time,
        0 * ureg.s,
        detect_frequencies / eo_parameters["order"],
        eo_amplitude,
        start_time=start_time
    )
    segment.add_awg_function(eo_parameters["channel"], eo_pulse)

    ao_pulse = AWGSineTrain(
        on_time,
        off_time,
        ao_parameters["frequency"],
        [ao_parameters["detect_amplitude"]] * len(detect_frequencies),
        start_time=start_time,
    )
    segment.add_awg_function(ao_parameters["channel"], ao_pulse)
    detect_ao_pulse = AWGSinePulse(
        detect_ao_parameters["frequency"], detect_ao_parameters["amplitude"],
    )
    segment.add_awg_function(detect_ao_parameters["channel"], detect_ao_pulse)
    segment._duration = segment.duration + ttl_detect_offset_time
    detect_read_time = segment.duration - ttl_start_time
    if field_plate_parameters["use"] and field_plate_parameters["on_polarity"]:
        segment.add_ttl_function(field_plate_parameters["channel"], TTLOff())
    else:
        segment.add_ttl_function(field_plate_parameters["channel"], TTLOn())
    return (segment, detect_read_time)
