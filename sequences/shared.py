from typing import Any
import warnings

import numpy as np
from onix.models.hyperfine import energies
from onix.sequences.sequence import (
    AWGFIDPulse,
    AWGHalfSineRamp,
    AWGSinePulse,
    AWGSimultaneousSinePulses,
    AWGDoubleSineSweep,
    AWGDoubleSineTrain,
    AWGHSHPulse,
    AWGConstant,
    AWGSineSweep,
    AWGSineTrain,
    MultiSegments,
    Segment,
    SegmentEmpty,
    Sequence,
    TTLOn,
    TTLPulses,
)
from onix.units import Q_, ureg
from onix.awg_maps import get_channel_from_name, get_ttl_channel_from_name
from onix.headers.rigol_field_plate import Rigol

# TODO: transition to optical detuning function.


def chasm_segment(
    name: str,
    ao_parameters: dict[str, Any],
    eos_parameters: dict[str, Any] | None,
    field_plate_parameters: dict[str, Any],
    chasm_parameters: dict[str, Any],
    rf_parameters: dict[str, Any],
    rf_pump_parameters: dict[str, Any],
):
    transitions = chasm_parameters["transitions"]
    scan = chasm_parameters["scan"]
    detunings = chasm_parameters["detunings"]
    ao_amplitude = chasm_parameters["ao_amplitude"]
    durations = chasm_parameters["durations"]
    repeats = chasm_parameters["repeats"]
    segments = []

    for kk, transition in enumerate(transitions):
        try:
            len(durations)
            duration = durations[kk]
        except TypeError:
            duration = durations
        try:
            len(detunings)
            detuning = detunings[kk]
        except TypeError:
            detuning = detunings

        segment_name = transition
        if transition.startswith("rf_"):
            parameters = rf_pump_parameters.copy()
            parameters["into"] = transition.split("_")[1]
            segments.append(_rf_pump_segment(segment_name, rf_parameters, parameters, duration))
        else:
            if not field_plate_parameters["use"]:
                polarities = [0]
            else:
                polarities = [-1, 1]
            for polarity in polarities:
                segments.append(
                    _scan_segment(
                        segment_name,
                        ao_parameters,
                        eos_parameters,
                        transition,
                        ao_amplitude,
                        duration,
                        scan,
                        detuning + field_plate_parameters["stark_shift"] * polarity,
                    )
                )
    segment = MultiSegments(name, segments)
    if field_plate_parameters["use"] and field_plate_parameters["during"]["chasm"]:
        field_plate = AWGConstant(field_plate_parameters["amplitude"])
        fp_channel = get_channel_from_name(field_plate_parameters["name"])
        segment.add_awg_function(fp_channel, field_plate)
    return (segment, repeats)


def antihole_segment(
    name: str,
    ao_parameters: dict[str, Any],
    eos_parameters: dict[str, Any] | None,
    field_plate_parameters: dict[str, Any],
    antihole_parameters: dict[str, Any],
    rf_parameters: dict[str, Any],
    rf_pump_parameters: dict[str, Any],
):
    transitions: list[str] = antihole_parameters["transitions"]
    scan = antihole_parameters["scan"]
    detunings = antihole_parameters["detunings"]
    ao_amplitudes = antihole_parameters["ao_amplitude"]
    durations = antihole_parameters["durations"]
    repeats = antihole_parameters["repeats"]
    segments = []

    for kk, transition in enumerate(transitions):
        try:
            len(durations)
            duration = durations[kk]
        except TypeError:
            duration = durations
        try:
            len(detunings)
            detuning = detunings[kk]
        except TypeError:
            detuning = detunings
        try:
            len(ao_amplitudes)
            ao_amplitude = ao_amplitudes[kk]
        except TypeError:
            ao_amplitude = ao_amplitudes

        segment_name = transition
        if transition.startswith("rf_"):
            rf_pump_parameters = rf_pump_parameters.copy()
            rf_pump_parameters["into"] = transition[3:]
            #segments.append(_rf_pump_segment(segment_name, rf_parameters, rf_pump_parameters, duration))
            
            if antihole_parameters["use_hsh"] == True:
                segments.append(_rf_pump_hsh_segment(segment_name, rf_parameters, rf_pump_parameters))
            else:            
                segments.append(_rf_pump_segment(segment_name, rf_parameters, rf_pump_parameters, duration))
        else:
            segments.append(
                _scan_segment(
                    segment_name,
                    ao_parameters,
                    eos_parameters,
                    transition,
                    ao_amplitude,
                    duration,
                    scan,
                    detuning,
                )
            )
    segment = MultiSegments(name, segments)
    
    if field_plate_parameters["use"] and field_plate_parameters["during"]["antihole"]:
        field_plate = AWGConstant(field_plate_parameters["amplitude"])
        fp_channel = get_channel_from_name(field_plate_parameters["name"])
        segment.add_awg_function(fp_channel, field_plate)
    return (segment, repeats)


def detect_segment(
    name: str,
    ao_parameters: dict[str, Any],
    eos_parameters: dict[str, Any] | None,
    field_plate_parameters: dict[str, Any],
    shutter_parameters: dict[str, Any],
    detect_parameters: dict[str, Any],
):
    segment = Segment(name)
    ttl_start_time = 0 * ureg.us  # digitizer trigger pulse start time.
    ttl_duration = 4 * ureg.us  # digitizer trigger pulse duration
    ttl_stop_time = ttl_start_time + ttl_duration
    detect_padding_time = 4 * ureg.us  # extra data recording time around the detection
    ttl_function = TTLPulses([[ttl_start_time, ttl_stop_time]])
    trigger_channel = get_ttl_channel_from_name(detect_parameters["name"])
    segment.add_ttl_function(trigger_channel, ttl_function)

    transition = detect_parameters["transition"]
    if eos_parameters is not None:
        eo_parameters = eos_parameters[transition]
        if transition is not None:  # TODO: use a shared transition name conversion function.
            F_state = transition[0]
            D_state = transition[1]
            frequency = (
                energies["5D0"][D_state]
                - energies["7F0"][F_state]
                + eo_parameters["offset"]
            )
        eo_amplitude = eo_parameters["amplitude"]
        eo_pulse = AWGSinePulse(frequency, eo_amplitude)
        eo_channel = get_channel_from_name(eo_parameters["name"])
        segment.add_awg_function(eo_channel, eo_pulse)

    detect_detunings = detect_parameters["detunings"]
    if field_plate_parameters["use"]:
        all_detunings = np.empty(
            (detect_detunings.size * 2,), dtype=detect_detunings.dtype
        )
        all_detunings *= detect_detunings.units
        # multiplied left side detect_detunings by -1 such that they are symmetric
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

    ao_frequencies = (
        ao_parameters["center_frequency"] + detect_detunings / ao_parameters["order"]
    )
    if detect_parameters["simultaneous"]:
        # ao_pulse = AWGSimultaneousSinePulses(

        # )
        raise NotImplementedError()
    elif "fid" in detect_parameters and detect_parameters["fid"]["use"]:
        probe_detuning = detect_parameters["fid"]["probe_detuning"]
        pump_amplitude = detect_parameters["fid"]["pump_amplitude"]
        pump_time = detect_parameters["fid"]["pump_time"]
        wait_time = detect_parameters["fid"]["wait_time"]
        probe_amplitude = detect_parameters["fid"]["probe_amplitude"]
        probe_time = detect_parameters["fid"]["probe_time"]
        phase = detect_parameters["fid"]["phase"] / ao_parameters["order"]
        ao_probe_frequency = ao_parameters["center_frequency"] + probe_detuning / ao_parameters["order"]
        ao_pulse = AWGFIDPulse(
            ao_frequencies,
            pump_amplitude,
            pump_time,
            wait_time,
            ao_probe_frequency,
            probe_amplitude,
            probe_time,
            phase,
            start_time = start_time + off_time / 2,
        )
    else:
        ao_pulse = AWGSineTrain(
            on_time,
            off_time,
            ao_frequencies,
            detect_parameters["ao_amplitude"],
            start_time = start_time + off_time / 2
        )
    
    ao_channel = get_channel_from_name(ao_parameters["name"])
    segment.add_awg_function(ao_channel, ao_pulse)

    segment.add_ttl_function(shutter_parameters["channel"], TTLOn())

    if "fid" in detect_parameters and detect_parameters["fid"]["use"]:
        probe_pulse_start = detect_parameters["fid"]["pump_time"] + detect_parameters["fid"]["wait_time"]
        detect_pulse_times = [
            (
                start_time + off_time / 2 + probe_pulse_start,
                start_time + off_time / 2 + probe_pulse_start + detect_parameters["fid"]["probe_time"],
            )
        ]
        detect_pulse_times = [
            (
                (pulse_start + ao_parameters["rise_delay"]).to("s").magnitude,
                (pulse_end + ao_parameters["fall_delay"]).to("s").magnitude,
            )
            for (pulse_start, pulse_end) in detect_pulse_times
        ]
        analysis_parameters = {
            "fid": True,
            "detect_detunings": detect_detunings,
            "digitizer_duration": segment.duration - ttl_start_time,
            "detect_pulse_times": detect_pulse_times,
        }
    else:
        detect_pulse_times = [
            (
                start_time + off_time / 2 + kk * (on_time + off_time),
                start_time + off_time / 2 + on_time + kk * (on_time + off_time),
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
            "fid": False,
            "detect_detunings": detect_detunings,
            "digitizer_duration": segment.duration - ttl_start_time,
            "detect_pulse_times": detect_pulse_times,
        }
    segment._duration = segment.duration + detect_parameters["delay"]
    if field_plate_parameters["use"] and field_plate_parameters["during"]["detect"]:
        if field_plate_parameters["method"] == "awg":
            field_plate = AWGConstant(field_plate_parameters["amplitude"])
            fp_channel = get_channel_from_name(field_plate_parameters["name"])
            segment.add_awg_function(fp_channel, field_plate)
    return (segment, analysis_parameters)
    

def _rf_pump_segment(
    name: str,
    rf_parameters: dict[str, Any],
    rf_pump_parameters: dict[str, Any],
    duration: Q_,
):
    segment = Segment(name)
    
    rf_channel = get_channel_from_name(rf_parameters["name"])
    lower_state = rf_parameters["transition"][0]
    upper_state = rf_parameters["transition"][1]
    offset = rf_parameters["offset"]
    center_frequency = energies["7F0"][upper_state] - energies["7F0"][lower_state] + offset
    scan_detunings = rf_pump_parameters["scan_detunings"][rf_pump_parameters["into"]]
    pulse = AWGSineSweep(
        center_frequency + scan_detunings[0],
        center_frequency + scan_detunings[1],
        rf_pump_parameters["amplitude"],
        0 * ureg.s,
        duration,
    )
    segment.add_awg_function(rf_channel, pulse)
    return segment

def _rf_pump_hsh_segment(
    name: str,
    rf_parameters: dict[str, Any],
    rf_pump_parameters: dict[str, Any],
):
    segment = Segment(name)
    
    rf_channel = get_channel_from_name(rf_parameters["name"])

    amplitude = rf_pump_parameters["amplitude"]
    T_0 = rf_pump_parameters["hsh"]["T_0"]
    T_ch = rf_pump_parameters["hsh"]["T_ch"]
    T_e = rf_pump_parameters["hsh"]["T_e"]

    lower_state = rf_parameters["transition"][0]
    upper_state = rf_parameters["transition"][1]
    offset = rf_parameters["offset"]
    center_frequency = energies["7F0"][upper_state] - energies["7F0"][lower_state] + offset
    scan_range = rf_pump_parameters["scan_detunings"][rf_pump_parameters["into"]] #rf_pump_parameters["hsh"]["scan_range"]
    scan_range = np.mean(scan_range)
    center_frequency += scan_range

    pulse_center = center_frequency #+ rf_pump_parameters["hsh"]["center_detuning"]
    pulse = AWGHSHPulse(amplitude, T_0, T_e, T_ch, pulse_center, scan_range)
    segment.add_awg_function(rf_channel, pulse)
    return segment

def _scan_segment(
    name: str,
    ao_parameters: dict[str, Any],
    eos_parameters: dict[str, Any] | None,
    transition: str,
    ao_amplitude: float,
    duration: Q_,
    scan: Q_,
    detuning: Q_ = 0 * ureg.Hz,
):
    segment = Segment(name, duration)
    if eos_parameters is not None:
        eo_parameters = eos_parameters[transition]
        F_state = transition[0]  # TODO: use a shared conversion function.
        D_state = transition[1]
        frequency = (
            energies["5D0"][D_state] - energies["7F0"][F_state] + eo_parameters["offset"]
        )
        eo_pulse = AWGSinePulse(frequency, eo_parameters["amplitude"])
        eo_channel = get_channel_from_name(eo_parameters["name"])
        segment.add_awg_function(eo_channel, eo_pulse)
    start = ao_parameters["center_frequency"] + (detuning - scan) / ao_parameters["order"]
    end = ao_parameters["center_frequency"] + (detuning + scan) / ao_parameters["order"]
    ao_pulse = AWGSineSweep(start, end, ao_amplitude, 0, duration)
    ao_channel = get_channel_from_name(ao_parameters["name"])
    segment.add_awg_function(ao_channel, ao_pulse)
    return segment


class SharedSequence(Sequence):
    def __init__(
        self,
        parameters: dict[str, Any],
        shutter_off_after_antihole: bool = False,
    ):
        super().__init__()
        self._ao_parameters = parameters["ao"]
        self._eos_parameters = parameters["eos"]
        self._field_plate_parameters = parameters["field_plate"]
        self._shutter_parameters = parameters["shutter"]
        self._chasm_parameters = parameters["chasm"]
        self._antihole_parameters = parameters["antihole"]
        self._rf_parameters = parameters["rf"]
        self._rf_pump_parameters = parameters["rf_pump"]
        self._detect_parameters = parameters["detect"]
        self._shutter_off_after_antihole = shutter_off_after_antihole
        self._define_chasm()
        self._define_antihole()
        self._define_detect()
        self._define_breaks()

    def _define_chasm(self):
        segment, self._chasm_repeats = chasm_segment(
            "chasm",
            self._ao_parameters,
            self._eos_parameters,
            self._field_plate_parameters,
            self._chasm_parameters,
            self._rf_parameters,
            self._rf_pump_parameters,
        )
        self.add_segment(segment)

    def _define_antihole(self):
        if not self._antihole_parameters["simultaneous"]:
            segment, self._antihole_repeats = antihole_segment(
                "antihole",
                self._ao_parameters,
                self._eos_parameters,
                self._field_plate_parameters,
                self._antihole_parameters,
                self._rf_parameters,
                self._rf_pump_parameters,
            )
            self.add_segment(segment)
        else:
            scan = self._antihole_parameters["scan"]
            center = self._ao_parameters["center_frequency"]
            order = self._ao_parameters["order"]
            detuning1 = 0 * ureg.MHz + self._antihole_parameters["detunings"]
            detuning2 = -17.95 * ureg.MHz + self._antihole_parameters["detunings"]
            start_frequency_1 = (detuning1 - scan) / order + center
            start_frequency_2 = (detuning2 - scan) / order + center
            stop_frequency_1 = (detuning1 + scan) / order + center
            stop_frequency_2 = (detuning2 + scan) / order + center
            duration = self._antihole_parameters["durations"]
            ao_amplitude_1 = self._antihole_parameters["ao_amplitude_1"]
            ao_amplitude_2 = self._antihole_parameters["ao_amplitude_2"]
            self._antihole_repeats = self._antihole_parameters["repeats"]

            rf_pump_parameters = self._rf_pump_parameters.copy()
            rf_pump_parameters["into"] = "b"
            segment = _rf_pump_segment("antihole", self._rf_parameters, rf_pump_parameters, duration)
            segment.add_awg_function(
                get_channel_from_name(self._ao_parameters["name"]),
                AWGDoubleSineSweep(
                    start_frequency_1,
                    stop_frequency_1,
                    ao_amplitude_1,
                    start_frequency_2,
                    stop_frequency_2,
                    ao_amplitude_2,
                    0 * ureg.s,
                    duration,
                )
            )
            if self._field_plate_parameters["use"] and self._field_plate_parameters["during"]["antihole"]:
                field_plate = AWGConstant(self._field_plate_parameters["amplitude"])
                fp_channel = get_channel_from_name(self._field_plate_parameters["name"])
                segment.add_awg_function(fp_channel, field_plate)
            self.add_segment(segment)

    def _define_detect(self):
        segment, self.analysis_parameters = detect_segment(
            "detect",
            self._ao_parameters,
            self._eos_parameters,
            self._field_plate_parameters,
            self._shutter_parameters,
            self._detect_parameters,
        )
        self.analysis_parameters["detect_groups"] = []
        self.add_segment(segment)

    def _define_breaks(self):
        break_time = 10 * ureg.us
        segment = SegmentEmpty("break", break_time)
        self.add_segment(segment)

        total_field_plate_time = self._field_plate_parameters["ramp_time"] + self._field_plate_parameters["padding_time"]
        segment_up = Segment("field_plate_ramp_up", total_field_plate_time)
        segment_down = Segment("field_plate_ramp_down", total_field_plate_time)
        if self._field_plate_parameters["use"]:
            field_plate_channel = get_channel_from_name(self._field_plate_parameters["name"])
            field_plate_up = AWGHalfSineRamp(
                0,
                self._field_plate_parameters["amplitude"],
                0 * ureg.s,
                self._field_plate_parameters["ramp_time"],
            )
            field_plate_down = AWGHalfSineRamp(
                self._field_plate_parameters["amplitude"],
                0,
                0 * ureg.s,
                self._field_plate_parameters["ramp_time"],
            )
            segment_up.add_awg_function(field_plate_channel, field_plate_up)
            segment_down.add_awg_function(field_plate_channel, field_plate_down)
        self.add_segment(segment_up)
        self.add_segment(segment_down)

        total_field_plate_time = self._field_plate_parameters["ramp_time"] + self._field_plate_parameters["padding_time"]
        segment_up_shutter = Segment("field_plate_ramp_up_shutter_on", total_field_plate_time)
        segment_down_shutter = Segment("field_plate_ramp_down_shutter_on", total_field_plate_time)
        if self._field_plate_parameters["use"]:
            field_plate_channel = get_channel_from_name(self._field_plate_parameters["name"])
            field_plate_up = AWGHalfSineRamp(
                0,
                self._field_plate_parameters["amplitude"],
                0 * ureg.s,
                self._field_plate_parameters["ramp_time"],
            )
            field_plate_down = AWGHalfSineRamp(
                self._field_plate_parameters["amplitude"],
                0,
                0 * ureg.s,
                self._field_plate_parameters["ramp_time"],
            )
            segment_up_shutter.add_awg_function(field_plate_channel, field_plate_up)
            segment_down_shutter.add_awg_function(field_plate_channel, field_plate_down)
        segment_up_shutter.add_ttl_function(self._shutter_parameters["channel"], TTLOn())
        segment_down_shutter.add_ttl_function(self._shutter_parameters["channel"], TTLOn())
        self.add_segment(segment_up_shutter)
        self.add_segment(segment_down_shutter)



        segment = Segment("shutter_break", break_time)
        segment.add_ttl_function(self._shutter_parameters["channel"], TTLOn())
        self.add_segment(segment)
        self._shutter_rise_delay_repeats = int(
            self._shutter_parameters["rise_delay"] / break_time
        )
        self._shutter_fall_delay_repeats = int(
            self._shutter_parameters["fall_delay"] / break_time
        )

    def get_detect_sequence(self, detect_cycles: int) -> list[tuple[str, int]]:
        segment_steps = []
        if self._field_plate_parameters["during"]["detect"]:
            segment_steps.append(("field_plate_ramp_up_shutter_on", 1))
        max_cycles = 1000000
        if detect_cycles <= max_cycles:
            segment_steps.append(("detect", detect_cycles))
        else:
            for _ in range(detect_cycles // max_cycles):
                segment_steps.append(("detect", max_cycles))
            segment_steps.append(("detect", detect_cycles % max_cycles))
        if self._field_plate_parameters["during"]["detect"]:
            segment_steps.append(("field_plate_ramp_down_shutter_on", 1))
        return segment_steps

    def get_chasm_sequence(self):
        segment_steps = []
        if self._field_plate_parameters["during"]["chasm"]:
            segment_steps.append(("field_plate_ramp_up", 1))
        segment_steps.append(("chasm", self._chasm_repeats))
        if self._field_plate_parameters["during"]["chasm"]:
            segment_steps.append(("field_plate_ramp_down", 1))
        detect_cycles = self._detect_parameters["cycles"]["chasm"]
        if detect_cycles > 0:
            segment_steps.append(("shutter_break", self._shutter_rise_delay_repeats))
            segment_steps.extend(self.get_detect_sequence(detect_cycles))
            self.analysis_parameters["detect_groups"].append(("chasm", detect_cycles))
            segment_steps.append(("break", self._shutter_fall_delay_repeats))
        return segment_steps

    def get_antihole_sequence(self):
        segment_steps = []
        if self._field_plate_parameters["during"]["antihole"]:
            segment_steps.append(("field_plate_ramp_up", 1))
        segment_steps.append(("antihole", self._antihole_repeats))
        if self._field_plate_parameters["during"]["antihole"]:
            segment_steps.append(("field_plate_ramp_down", 1))
        segment_steps.append(("break", int(self._antihole_parameters["detect_delay"]/(10 * ureg.us))))
        segment_steps.append(("shutter_break", self._shutter_rise_delay_repeats))
        detect_cycles = self._detect_parameters["cycles"]["antihole"]
        if detect_cycles > 0:
            segment_steps.extend(self.get_detect_sequence(detect_cycles))
            self.analysis_parameters["detect_groups"].append(("antihole", detect_cycles))
        segment_steps.append(("shutter_break", 1))
        if self._shutter_off_after_antihole:
            segment_steps.append(("break", self._shutter_fall_delay_repeats))
        return segment_steps

    def get_rf_sequence(self):
        """This must be defined in derived classes."""
        raise NotImplementedError()

    def setup_sequence(self, use_opposite_field=False):
        segment_steps = []
        self._field_plate_parameters["use_opposite_field"] = False
        segment_steps.extend(self.get_chasm_sequence())
        segment_steps.extend(self.get_antihole_sequence())
        segment_steps.extend(self.get_rf_sequence())
        return super().setup_sequence(segment_steps)

    def num_of_record_cycles(self):
        total_cycles = 0
        for name, cycles in self.analysis_parameters["detect_groups"]:
            total_cycles += cycles
        return total_cycles
