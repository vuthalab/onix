"""AWG implementation of the experiment sequence steps."""
from typing import Any, Optional

from matplotlib import pyplot as plt
import numpy as np

from onix.control.awg_maps import (
    get_awg_channel_from_name, get_ttl_channel_from_name
)
from onix.control import (
    unify_lists, list_to_array
)
from onix.control.hardware import voltage_to_awg_amplitude
from onix.control.segments import Segment, MultiSegments
from onix.control.awg_functions import (
    AWGCompositePulse, AWGHSHPulse, AWGSinePulse, AWGSineSweep, AWGSineTrain
)
from onix.control.ttl_functions import TTLOn, TTLPulses
from onix.units import Q_, ureg


def _add_shutter_ttl(segment: Segment, parameters: dict[str, Any]):
    shutter_params = parameters["shutter"]
    segment.add_ttl_function(
        get_ttl_channel_from_name(shutter_params["channel_name"]),
        TTLOn(),
    )


def _relative_optical_transition_frequency(
        state_7F0: str, state_5D0: str, parameters: dict[str, Any]
    ) -> Q_:
    """Optical transition frequency relative to the 7F0, a -> 5D0, c tranistion."""
    hyperfine_params = parameters["hyperfine"]
    return (
        (hyperfine_params["5D0"][state_5D0] - hyperfine_params["5D0"]["c"])
        - (hyperfine_params["7F0"][state_7F0] - hyperfine_params["7F0"]["a"])
    )


def _optical_detuning_to_ao_shift(
    detuning: Q_, parameters: dict[str, Any], transition: Optional[str] = None,
) -> Q_:
    if transition is None:
        transition = "ac"
    ao_params = parameters["ao"]
    ao_order = ao_params["order"]
    if transition is None:
        transition = "ac"
    transition_detuning = _relative_optical_transition_frequency(
        transition[0], transition[1], parameters
    )
    return (transition_detuning + detuning) / ao_order


def _optical_detuning_to_ao_frequency(
    detuning: Q_, parameters: dict[str, Any], transition: Optional[str] = None,
) -> Q_:
    ao_frequency_ac = parameters["ao"]["frequency_ac"]
    return ao_frequency_ac + _optical_detuning_to_ao_shift(detuning, parameters, transition)


def _optical_scan_segment(
    name: str,
    parameters: dict[str, Any],
    transition: str,
    center_detuning: Q_,
    scan: Q_,
    ao_amplitude: Q_,
    duration: Q_,
):
    segment = Segment(name, duration)
    start_ao_freq = _optical_detuning_to_ao_frequency(
        center_detuning - scan, parameters, transition
    )
    end_ao_freq = _optical_detuning_to_ao_frequency(
        center_detuning + scan, parameters, transition
    )

    ao_pulse = AWGSineSweep(start_ao_freq, end_ao_freq, ao_amplitude, 0 * ureg.s, duration)
    ao_channel = get_awg_channel_from_name(parameters["ao"]["channel_name"])
    segment.add_awg_function(ao_channel, ao_pulse)
    return segment


def _delay_segment(parameters: dict[str, Any], E_field_on: bool = False, shutter_on: bool = False) -> Segment:
    segment = Segment(f"delay_E_field_{E_field_on}_shutter_{shutter_on}", duration=10 * ureg.us)
    segment.set_electric_field(E_field_on)
    if shutter_on:
        _add_shutter_ttl(segment, parameters)
    return segment


def _electric_field_rise_segment_and_steps(parameters: dict[str, Any], shutter_on: bool = False) -> tuple[Segment, int]:
    segment = _delay_segment(parameters, E_field_on=True, shutter_on=shutter_on)
    rise_total_time = (
        parameters["field_plate"]["rise_ramp_time"]
        + parameters["field_plate"]["rise_delay_time"]
    )
    return (segment, int(np.ceil(rise_total_time / segment.actual_duration)))


def _electric_field_fall_segment_and_steps(parameters: dict[str, Any], shutter_on: bool = False) -> tuple[Segment, int]:
    segment = _delay_segment(parameters, E_field_on=False, shutter_on=shutter_on)
    fall_total_time = (
        parameters["field_plate"]["fall_ramp_time"]
        + parameters["field_plate"]["fall_delay_time"]
    )
    return (segment, int(np.ceil(fall_total_time / segment.actual_duration)))


def _shutter_rise_segment_and_steps(parameters: dict[str, Any], E_field_on: bool = False) -> tuple[Segment, int]:
    segment = _delay_segment(parameters, E_field_on=E_field_on, shutter_on=True)
    rise_delay = parameters["shutter"]["rise_delay"]
    return (segment, int(np.ceil(rise_delay / segment.actual_duration)))


def _shutter_fall_segment_and_steps(parameters: dict[str, Any], E_field_on: bool = False) -> tuple[Segment, int]:
    segment = _delay_segment(parameters, E_field_on=E_field_on, shutter_on=False)
    fall_delay = parameters["shutter"]["fall_delay"]
    return (segment, int(np.ceil(fall_delay / segment.actual_duration)))


def chasm_segments(
    sequence_step_name: str,
    parameters: dict[str, Any],
) -> tuple[list[tuple[Segment, int]], list[tuple[str]]]:
    chasm_params = parameters["chasm"]
    transitions = chasm_params["transitions"]
    detunings = chasm_params["detunings"]
    scans = chasm_params["scans"]
    amplitudes = voltage_to_awg_amplitude(chasm_params["amplitudes"])
    durations = chasm_params["durations"]
    repeats = chasm_params["repeats"]

    # convert transitions to a list if not one already.
    transitions,  = unify_lists(transitions)
    # make all other variables the same length as transitions
    detunings, scans, amplitudes, durations = unify_lists(
        detunings, scans, amplitudes, durations, length=len(transitions)
    )
    detunings = list_to_array(detunings, "Hz")
    scans = list_to_array(scans, "Hz")
    durations = list_to_array(durations, "s")

    # define the optical pulses
    sub_segments = []

    field_plate_params = parameters["field_plate"]
    # if field plate is on, needs to scan two chasms.
    field_on = field_plate_params["use"] and "chasm" in field_plate_params["during"]
    if not field_on:
        Pi_values = [0]
    else:
        if field_plate_params["negative_Pi_first"]:
            Pi_values = [-1, 1]
        else:
            Pi_values = [1, -1]
    for kk, transition in enumerate(transitions):
        for Pi in Pi_values:
            this_segment_name = f"{kk}_{transition}_{Pi}"
            E_field = field_plate_params["voltage_to_field"] * field_plate_params["high_voltage"] * field_plate_params["amplifier_voltage_gain"]
            abs_E_field_shift = abs(E_field * field_plate_params["dipole_moment"])
            E_field_shift = Pi * abs_E_field_shift
            center_detuning = detunings[kk] + E_field_shift
            sub_segments.append(
                _optical_scan_segment(
                    this_segment_name,
                    parameters,
                    transition,
                    center_detuning,
                    scans[kk],
                    amplitudes[kk],
                    durations[kk],
                )
            )
    # combines all chasm segments into a single one.
    segment = MultiSegments(sequence_step_name, sub_segments)
    if field_on:
        segment.set_electric_field(True)

    segments_and_steps: list[tuple[Segment, int]] = []
    if field_on:
        # the E field needs to be turned on.
        segments_and_steps.append(_electric_field_rise_segment_and_steps(parameters))
    segments_and_steps.append((segment, repeats))
    if field_on:
        # the E field needs to be turned off.
        segments_and_steps.append(_electric_field_fall_segment_and_steps(parameters))
    segments_and_steps.append((_delay_segment(parameters), 1))

    parameters_iterate_this_segment = []  # chasm is not compatible with parameter iteration.
    return segments_and_steps, parameters_iterate_this_segment


def antihole_segments(
    sequence_step_name: str,
    parameters: dict[str, Any],
) -> tuple[list[tuple[Segment, int]], list[tuple[str]]]:
    ah_params = parameters["antihole"]
    transitions = ah_params["transitions"]
    detunings = ah_params["detunings"]
    amplitudes = voltage_to_awg_amplitude(ah_params["amplitudes"])
    durations = ah_params["durations"]
    repeats = ah_params["repeats"]

    # convert transitions to a list if not one already.
    transitions,  = unify_lists(transitions)
    # make all other variables the same length as transitions
    detunings, amplitudes, durations = unify_lists(
        detunings, amplitudes, durations, length=len(transitions)
    )
    detunings = list_to_array(detunings, "Hz")
    durations = list_to_array(durations, "s")
    
    # define the optical pulses
    sub_segments = []

    field_plate_params = parameters["field_plate"]
    # if field plate is on, needs to scan two chasms.
    field_on = field_plate_params["use"] and "antihole" in field_plate_params["during"]
    for kk, transition in enumerate(transitions):
        this_segment_name = f"{kk}_{transition}"
        scan = 0 * ureg.Hz
        sub_segments.append(
            _optical_scan_segment(
                this_segment_name,
                parameters,
                transition,
                detunings[kk],
                scan,
                amplitudes[kk],
                durations[kk],
            )
        )
    # combines all antihole segments into a single one.
    segment = MultiSegments(sequence_step_name, sub_segments)
    if field_on:
        segment.set_electric_field(True)

    segments_and_steps: list[tuple[Segment, int]] = []
    if field_on:
        # the E field needs to be turned on.
        segments_and_steps.append(_electric_field_rise_segment_and_steps(parameters))
    segments_and_steps.append((segment, repeats))
    if field_on:
        # the E field needs to be turned off.
        segments_and_steps.append(_electric_field_fall_segment_and_steps(parameters))
    segments_and_steps.append((_delay_segment(parameters), 1))

    parameters_iterate_this_segment = []  # antihole is not compatible with parameter iteration.
    return segments_and_steps, parameters_iterate_this_segment


def detect_segments(
    sequence_step_name: str,
    parameters: dict[str, Any],
) -> tuple[list[tuple[Segment, int]], list[tuple[str]]]:
    ttl_start_time = 0 * ureg.us  # digitizer trigger pulse start time.
    ttl_duration = 4 * ureg.us  # digitizer trigger pulse duration
    ttl_stop_time = ttl_start_time + ttl_duration
    
    segment = Segment(sequence_step_name)
    _add_shutter_ttl(segment, parameters)
    ttl_function = TTLPulses([[ttl_start_time, ttl_stop_time]])
    trigger_channel = get_ttl_channel_from_name(parameters["digitizer"]["channel_name"])
    segment.add_ttl_function(trigger_channel, ttl_function)

    field_plate_params = parameters["field_plate"]
    field_on = field_plate_params["use"] and "detect" in field_plate_params["during"]
    if not field_on:
        Pi_values = [0]
    else:
        if field_plate_params["negative_Pi_first"]:
            Pi_values = [-1, 1]
        else:
            Pi_values = [1, -1]

    detect_params = parameters["detect"]
    mode = detect_params["mode"]

    if mode == "abs":
        detect_mode_params = detect_params["abs"]
        detunings_MHz = detect_mode_params["detunings"].to("MHz").magnitude
        all_detunings = np.empty(
            (detunings_MHz.size * len(Pi_values),), dtype=detunings_MHz.dtype
        )
        for kk, Pi in enumerate(Pi_values):
            E_field = field_plate_params["voltage_to_field"] * field_plate_params["high_voltage"] * field_plate_params["amplifier_voltage_gain"]
            abs_E_field_shift = abs(E_field * field_plate_params["dipole_moment"])
            E_field_shift = Pi * abs_E_field_shift
            all_detunings[kk::len(Pi_values)] = detunings_MHz + E_field_shift.to("MHz").magnitude
        all_detunings *= ureg.MHz
        
        ao_freqs = _optical_detuning_to_ao_frequency(
            all_detunings, parameters, detect_mode_params["transition"]
        )
        on_time = detect_mode_params["on_time"]
        off_time = detect_mode_params["off_time"]
        detect_start_time = ttl_stop_time + off_time / 2
        ao_pulse = AWGSineTrain(
            on_time,
            off_time,
            ao_freqs,
            voltage_to_awg_amplitude(detect_mode_params["amplitude"]),
            start_time = detect_start_time,
        )
        ao_channel = get_awg_channel_from_name(parameters["ao"]["channel_name"])
        segment.add_awg_function(ao_channel, ao_pulse)

        detect_pulse_times = [
            (
                detect_start_time + off_time / 2 + kk * (on_time + off_time),
                detect_start_time + off_time / 2 + on_time + kk * (on_time + off_time),
            )
            for kk in range(len(all_detunings))
        ]
        detect_pulse_times = [
            (
                (pulse_start + parameters["ao"]["rise_delay"]).to("s").magnitude,
                (pulse_end + parameters["ao"]["fall_delay"]).to("s").magnitude,
            )
            for (pulse_start, pulse_end) in detect_pulse_times
        ]
        segment.additional_detection_parameters = {
            "mode": mode,
            "detunings": all_detunings,
            "duration": segment.duration - ttl_start_time,
            "pulse_times": detect_pulse_times,
        }
        segment._duration = segment.actual_duration + detect_mode_params["delay"]
    elif mode == "fid":
        raise NotImplementedError("FID mode is not implemented.")
    else:
        raise NotImplementedError(f"Mode {mode} is not defined.")

    if field_on:
        segment.set_electric_field(True)

    segments_and_steps: list[tuple[Segment, int]] = []
    segments_and_steps.append(_shutter_rise_segment_and_steps(parameters))
    if field_on:
        # the E field needs to be turned on.
        segments_and_steps.append(_electric_field_rise_segment_and_steps(parameters, shutter_on=True))
    segments_and_steps.append((segment, detect_mode_params["repeats"]))
    if field_on:
        # the E field needs to be turned off.
        segments_and_steps.append(_electric_field_fall_segment_and_steps(parameters, shutter_on=False))
    segments_and_steps.append(_shutter_fall_segment_and_steps(parameters))
    segments_and_steps.append((_delay_segment(parameters), 1))

    parameters_iterate_this_segment = []  # detect is not compatible with parameter iteration.
    return segments_and_steps, parameters_iterate_this_segment


def rf_sweep_segments(
    sequence_step_name: str,
    parameters: dict[str, Any],
) -> tuple[list[tuple[Segment, int]], list[tuple[str]]]:
    rf_params = parameters["rf"]["sweep"]
    rf_avg_freq = parameters["rf"]["avg_center_frequency"]
    if "abar_to_bbar" in sequence_step_name:
        rf_scan_center = rf_params["detuning_abar_to_bbar"] + rf_avg_freq
    elif "a_to_b" in sequence_step_name:
        rf_scan_center = rf_params["detuning_a_to_b"] + rf_avg_freq
    else:
        raise ValueError(f"Step name {sequence_step_name} is not a valid rf sweep name.")
    
    rf_channel = get_awg_channel_from_name(parameters["rf"]["channel_name"])
    amplitude = voltage_to_awg_amplitude(rf_params["amplitude"])
    T_0 = rf_params["T_0"]
    T_e = rf_params["T_e"]
    T_ch = rf_params["T_ch"]
    scan = rf_params["scan"]
    segment = Segment(sequence_step_name)
    pulse = AWGHSHPulse(amplitude, T_0, T_e, T_ch, rf_scan_center, scan)
    segment.add_awg_function(rf_channel, pulse)

    field_plate_params = parameters["field_plate"]
    field_on = field_plate_params["use"] and "rf_sweep" in field_plate_params["during"]

    segments_and_steps: list[tuple[Segment, int]] = []
    if field_on:
        # the E field needs to be turned on.
        segments_and_steps.append(_electric_field_rise_segment_and_steps(parameters, shutter_on=True))
    segments_and_steps.append((segment, 1))
    if field_on:
        # the E field needs to be turned off.
        segments_and_steps.append(_electric_field_fall_segment_and_steps(parameters, shutter_on=True))
    segments_and_steps.append((_delay_segment(parameters), 1))

    parameters_iterate_this_segment = []  # rf sweep is not compatible with parameter iteration.
    return segments_and_steps, parameters_iterate_this_segment


def rf_rabi_segments(
    sequence_step_name: str,
    parameters: dict[str, Any],
) -> tuple[list[tuple[Segment, int]], list[tuple[str]]]:
    rf_params = parameters["rf"]["rabi"]
    center_frequency = parameters["rf"]["avg_center_frequency"]
    detuning = rf_params["detuning"]
    amplitude = voltage_to_awg_amplitude(rf_params["amplitude"])
    duration = rf_params["duration"]

    segment = Segment(sequence_step_name, duration)
    rf_channel = get_awg_channel_from_name(parameters["rf"]["channel_name"])
    segment.add_awg_function(
        rf_channel,
        AWGSinePulse(center_frequency + detuning, amplitude)
    )

    field_plate_params = parameters["field_plate"]
    field_on = field_plate_params["use"] and "rf_rabi" in field_plate_params["during"]

    segments_and_steps: list[tuple[Segment, int]] = []
    if field_on:
        # the E field needs to be turned on.
        segments_and_steps.append(_electric_field_rise_segment_and_steps(parameters, shutter_on=True))
    segments_and_steps.append((segment, 1))
    if field_on:
        # the E field needs to be turned off.
        segments_and_steps.append(_electric_field_fall_segment_and_steps(parameters, shutter_on=True))
    segments_and_steps.append((_delay_segment(parameters), 1))

    parameters_iterate_this_segment = [
        ("rf", "rabi", "detuning"),
        ("rf", "rabi", "amplitude"),
        ("rf", "rabi", "duration"),
    ]
    return segments_and_steps, parameters_iterate_this_segment


def lf_equilibrate_segments(
    sequence_step_name: str,
    parameters: dict[str, Any],
) -> tuple[list[tuple[Segment, int]], list[tuple[str]]]:
    lf_params = parameters["lf"]["equilibrate"]
    center_frequency = lf_params["center_frequency"]
    Sigma = lf_params["Sigma"]
    Zeeman_shift_along_b = lf_params["Zeeman_shift_along_b"]
    detuning = lf_params["detuning"]
    amplitude = voltage_to_awg_amplitude(lf_params["piov2_amplitude"])
    duration = lf_params["piov2_duration"]
    use_composite = lf_params["use_composite"]
    composite_segments = lf_params["composite_segments"]
    lf_pulse_freq = center_frequency + Zeeman_shift_along_b * Sigma + detuning

    lf_channel = get_awg_channel_from_name(parameters["lf"]["channel_name"])
    segment = Segment(sequence_step_name)
    if not use_composite:
        segment.add_awg_function(
            lf_channel,
            AWGSinePulse(lf_pulse_freq, amplitude, end_time=duration)
        )
    else:
        # Malcolm H. Levitt, Composite Pulses
        if composite_segments == 3:
            durations = np.array([385.0, 320.0, 25.0]) / 90 * duration
            phases = np.deg2rad([0.0, 180.0, 0.0])
        else:
            raise NotImplementedError(f"Composite pulse segments of {composite_segments} is not implemented.")
        segment.add_awg_function(
            lf_channel,
            AWGCompositePulse(
                durations,
                [lf_pulse_freq] * composite_segments,
                [amplitude] * composite_segments,
                phases,
            )
        )

    field_plate_params = parameters["field_plate"]
    field_on = field_plate_params["use"] and "lf_equilibrate" in field_plate_params["during"]

    segments_and_steps: list[tuple[Segment, int]] = []
    if field_on:
        # the E field needs to be turned on.
        segments_and_steps.append(_electric_field_rise_segment_and_steps(parameters, shutter_on=True))
    segments_and_steps.append((segment, 1))
    if field_on:
        # the E field needs to be turned off.
        segments_and_steps.append(_electric_field_fall_segment_and_steps(parameters, shutter_on=True))
    segments_and_steps.append((_delay_segment(parameters), 1))
    parameters_iterate_this_segment = [
        ("lf", "equilibrate", "center_frequency"),
        ("lf", "equilibrate", "Zeeman_shift_along_b"),
        ("lf", "equilibrate", "Sigma"),
        ("lf", "equilibrate", "detuning"),
        ("lf", "equilibrate", "piov2_amplitude"),
        ("lf", "equilibrate", "piov2_duration"),
    ]
    return segments_and_steps, parameters_iterate_this_segment


def lf_rabi_segments(
    sequence_step_name: str,
    parameters: dict[str, Any],
) -> tuple[list[tuple[Segment, int]], list[tuple[str]]]:
    lf_params = parameters["lf"]["rabi"]
    center_frequency = lf_params["center_frequency"]
    Sigma = lf_params["Sigma"]
    Zeeman_shift_along_b = lf_params["Zeeman_shift_along_b"]
    detuning = lf_params["detuning"]
    amplitude = voltage_to_awg_amplitude(lf_params["amplitude"])
    duration = lf_params["duration"]

    segment = Segment(sequence_step_name, duration)
    lf_channel = get_awg_channel_from_name(parameters["lf"]["channel_name"])
    segment.add_awg_function(
        lf_channel,
        AWGSinePulse(
            center_frequency + Zeeman_shift_along_b * Sigma + detuning, amplitude
        )
    )

    segments_and_steps: list[tuple[Segment, int]] = [
        (segment, 1),
        (_delay_segment(parameters), 1),
    ]
    parameters_iterate_this_segment = [
        ("lf", "rabi", "center_frequency"),
        ("lf", "rabi", "Zeeman_shift_along_b"),
        ("lf", "rabi", "Sigma"),
        ("lf", "rabi", "detuning"),
        ("lf", "rabi", "amplitude"),
        ("lf", "rabi", "duration"),
    ]
    return segments_and_steps, parameters_iterate_this_segment


def lf_ramsey_segments(
    sequence_step_name: str,
    parameters: dict[str, Any],
) -> tuple[list[tuple[Segment, int]], list[tuple[str]]]:
    lf_params = parameters["lf"]["ramsey"]
    center_frequency = lf_params["center_frequency"]
    Sigma = lf_params["Sigma"]
    Zeeman_shift_along_b = lf_params["Zeeman_shift_along_b"]
    detuning = lf_params["detuning"]
    amplitude = voltage_to_awg_amplitude(lf_params["amplitude"])
    piov2_time = lf_params["piov2_time"]
    wait_time = lf_params["wait_time"]
    phase = lf_params["phase"]
    lf_freq = center_frequency + Zeeman_shift_along_b * Sigma + detuning

    segment = Segment(sequence_step_name)
    lf_channel = get_awg_channel_from_name(parameters["lf"]["channel_name"])
    segment.add_awg_function(
        lf_channel,
        AWGCompositePulse(
            [piov2_time, wait_time, piov2_time],
            [lf_freq, 0, lf_freq],
            [amplitude, 0, amplitude],
            [0, 0, phase],
        )
    )

    segments_and_steps: list[tuple[Segment, int]] = [
        (segment, 1),
        (_delay_segment(parameters), 1),
    ]
    parameters_iterate_this_segment = [
        ("lf", "ramsey", "center_frequency"),
        ("lf", "ramsey", "Zeeman_shift_along_b"),
        ("lf", "ramsey", "Sigma"),
        ("lf", "ramsey", "detuning"),
        ("lf", "ramsey", "amplitude"),
        ("lf", "ramsey", "piov2_time"),
        ("lf", "ramsey", "wait_time"),
        ("lf", "ramsey", "phase"),
    ]
    return segments_and_steps, parameters_iterate_this_segment


def delay_segments(
    sequence_step_name: str,
    parameters: dict[str, Any],
) -> tuple[list[tuple[Segment, int]], list[tuple[str]]]:
    time_ms = int(sequence_step_name.split("_")[-1])

    segment = Segment("delay_1ms", duration=1 * ureg.ms)
    segments_and_steps: list[tuple[Segment, int]] = [
        (segment, time_ms),
    ]
    parameters_iterate_this_segment = []
    return segments_and_steps, parameters_iterate_this_segment


name_to_segment_builder = {
    "chasm": chasm_segments,
    "antihole": antihole_segments,
    "detect": detect_segments,
    "rf_sweep": rf_sweep_segments,
    "rf_rabi": rf_rabi_segments,
    "lf_equilibrate": lf_equilibrate_segments,
    "lf_rabi": lf_rabi_segments,
    "lf_ramsey": lf_ramsey_segments,
    "delay": delay_segments,
}
