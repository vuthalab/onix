import numbers
from typing import Optional, Union
from typing import Any
import warnings

import numpy as np

from onix.models.hyperfine import energies
from onix.sequences.sequence import (
    AWGConstant,
    AWGFunction,
    AWGMultiFunctions,
    AWGSinePulse,
    Segment,
    TTLOn,
    TTLPulses,
)
from onix.sequences.shared import SharedSequence
from onix.units import Q_, ureg
from onix.awg_maps import get_channel_from_name


class AWGMultipleSinePulse(AWGFunction):
    def __init__(
        self,
        frequencies: Union[list[float], Q_],
        amplitude: float,
        phase: float = 0,
        start_time: Optional[Union[float, Q_]] = None,
        end_time: Optional[Union[float, Q_]] = None,
    ):
        super().__init__()
        if not isinstance(frequencies, Q_):
            for kk in range(len(frequencies)):
                if isinstance(frequencies[kk], numbers.Number):
                    frequencies[kk] = frequencies[kk] * ureg.Hz
            frequencies = Q_.from_list(frequencies, "Hz")
        self._frequencies = frequencies
        self._amplitude = amplitude
        self._phase = phase
        if isinstance(start_time, numbers.Number):
            start_time = start_time * ureg.s
        self._start_time: Union[Q_, None] = start_time
        if isinstance(end_time, numbers.Number):
            end_time = end_time * ureg.s
        self._end_time: Union[Q_, None] = end_time

    def output(self, times):
        frequencies = self._frequencies.to("Hz").magnitude
        sine = np.zeros(len(times))
        for frequency in frequencies:
            sine += self._amplitude * np.sin(2 * np.pi * frequency * times + self._phase)
        if self._start_time is not None:
            start_time = self._start_time.to("s").magnitude
            mask_start = np.heaviside(times - start_time, 0)
        else:
            mask_start = 1
        if self._end_time is not None:
            end_time = self._end_time.to("s").magnitude
            mask_end = np.heaviside(end_time - times, 1)
        else:
            mask_end = 1
        return sine * mask_start * mask_end

    @property
    def min_duration(self) -> Q_:
        if self._end_time is not None:
            return self._end_time
        if self._start_time is not None:
            return self._start_time
        return 0 * ureg.s

    @property
    def max_amplitude(self):
        return self._amplitude


def fid_detect_segment(
    name: str,
    ao_parameters: dict[str, Any],
    eos_parameters: dict[str, Any],
    field_plate_parameters: dict[str, Any],
    shutter_parameters: dict[str, Any],
    fid_detect_parameters: dict[str, Any],
):
    segment = Segment(name)
    # eo pulse
    transition = fid_detect_parameters["transition"]
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

    # ao pulse
    pump_detunings = np.array([0]) * ureg.Hz
    probe_detuning = fid_detect_parameters["probe_detuning"]
    if field_plate_parameters["use"]:
        all_detunings = np.empty(
            (pump_detunings.size * 2,), dtype=pump_detunings.dtype
        )
        all_detunings *= pump_detunings.units
        all_detunings[0::2] = pump_detunings - field_plate_parameters["stark_shift"]
        all_detunings[1::2] = pump_detunings + field_plate_parameters["stark_shift"]
        pump_detunings = all_detunings  # [- field_plate_parameters["stark_shift"], field_plate_parameters["stark_shift"]]

    ao_pump_frequencies = (
        ao_parameters["center_frequency"] + pump_detunings / ao_parameters["order"]
    )
    ao_pump_pulse = AWGMultipleSinePulse(
        ao_pump_frequencies, fid_detect_parameters["ao_pump_amplitude"]
    )
    ao_probe_frequency = (
        ao_parameters["center_frequency"] + probe_detuning / ao_parameters["order"]
    )
    ao_probe_pulse = AWGSinePulse(
        ao_probe_frequency,
        fid_detect_parameters["ao_probe_amplitude"],
        fid_detect_parameters["probe_phase"] / ao_parameters["order"],
    )
    pump_time = fid_detect_parameters["pump_time"]
    probe_time = fid_detect_parameters["probe_time"]
    delay_time = fid_detect_parameters["delay_time"]
    ao_pulse = AWGMultiFunctions(
        [ao_pump_pulse, ao_probe_pulse],
        [0 * ureg.s, pump_time],
        [pump_time, pump_time + delay_time + probe_time],
    )
    ao_channel = get_channel_from_name(ao_parameters["name"])
    segment.add_awg_function(ao_channel, ao_pulse)

    # shutter pulse
    segment.add_ttl_function(shutter_parameters["channel"], TTLOn())
    
    # trigger pulse
    ttl_start_time = pump_time + delay_time  # digitizer trigger pulse start time.
    ttl_duration = pump_time + delay_time + 4 * ureg.us  # digitizer trigger pulse duration
    ttl_function = TTLPulses([[ttl_start_time, ttl_start_time + ttl_duration]])
    segment.add_ttl_function(fid_detect_parameters["trigger_channel"], ttl_function)

    analysis_parameters = {
        "digitizer_duration": fid_detect_parameters["probe_time"],
    }
    segment._duration = segment.duration + fid_detect_parameters["delay"]
    return (segment, analysis_parameters)


class AntiholeFID(SharedSequence):
    def __init__(self, parameters: dict[str, Any]):
        self._fid_detect_parameters = parameters["fid_detect"]
        super().__init__(parameters, shutter_off_after_antihole=False)

    def _define_detect(self):
        segment, self.analysis_parameters = fid_detect_segment(
            "detect",
            self._ao_parameters,
            self._eos_parameters,
            self._field_plate_parameters,
            self._shutter_parameters,
            self._fid_detect_parameters,
        )
        self.analysis_parameters["detect_groups"] = []
        self.add_segment(segment)

    def get_antihole_sequence(self):
        segment_steps = []
        # waiting for the field plate to go high
        segment_steps.append(("field_plate_break", self._field_plate_break_repeats))
        segment_steps.append(("antihole", self._antihole_repeats))
        # waiting for the field plate to go low
        segment_steps.append(("break", self._field_plate_break_repeats))
        segment_steps.append(("break", 10000))
        segment_steps.append(("shutter_break", self._shutter_rise_delay_repeats))
        detect_cycles = self._fid_detect_parameters["cycles"]["antihole"]
        segment_steps.extend(self.get_detect_sequence(detect_cycles))
        self.analysis_parameters["detect_groups"].append(("antihole", detect_cycles))
        segment_steps.append(("shutter_break", 1))
        if self._shutter_off_after_antihole:
            segment_steps.append(("break", self._shutter_fall_delay_repeats))
        return segment_steps

    def get_rf_sequence(self):
        return []
