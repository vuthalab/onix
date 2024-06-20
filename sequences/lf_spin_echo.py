from typing import Any
from onix.sequences.sequence import (
    AWGHSHPulse,
    AWGSpinEcho,
    AWGSineSweep,
    Segment,
    TTLOn,
)
from onix.models.hyperfine import energies
from onix.sequences.shared import SharedSequence
from onix.awg_maps import get_channel_from_name
import numpy as np
from onix.units import ureg


class LFSpinEcho(SharedSequence):
    """
    Spin echo sequence for a -> abar and b -> bbar transitions.
    """
    def __init__(self, parameters: dict[str, Any]):
        super().__init__(parameters, shutter_off_after_antihole=True)
        self._lf_parameters = parameters["lf"]
        self._define_lf()
        self._define_rf()

    def _define_lf(self):
        lf_channel = get_channel_from_name(self._rf_parameters["name"])
        center_frequency =  self._lf_parameters["center_frequency"]
        detuning = self._lf_parameters["detuning"]
        amplitude = self._lf_parameters["amplitude"]
        segment = Segment("lf")

        piov2_time = self._lf_parameters["piov2_time"]
        pi_time = self._lf_parameters["pi_time"]
        delay_time = self._lf_parameters["delay_time"]
        phase = self._lf_parameters["phase"]
        phase_pi = self._lf_parameters["phase_pi"]

        pulse = AWGSpinEcho(piov2_time, pi_time, delay_time, center_frequency + detuning, amplitude, phase, phase_pi)
        segment.add_awg_function(lf_channel, pulse)
        if not self._shutter_off_after_antihole:
            segment.add_ttl_function(self._shutter_parameters["channel"], TTLOn())
        self.add_segment(segment)


    def _define_rf(self):
        rf_channel = get_channel_from_name(self._rf_parameters["name"])
        amplitude = self._rf_parameters["amplitude"]
        T_0 = self._rf_parameters["T_0"]
        T_e = self._rf_parameters["T_e"]
        T_ch = self._rf_parameters["T_ch"]
        lower_state = self._rf_parameters["transition"][0]
        upper_state = self._rf_parameters["transition"][1]
        offset = self._rf_parameters["offset"]
        center_frequency = energies["7F0"][upper_state] - energies["7F0"][lower_state] + offset
        pulse_center = self._rf_parameters["center_detuning"] + center_frequency
        scan_range = self._rf_parameters["scan_range"]
        if self._rf_parameters["use_hsh"]:
            pulse = AWGHSHPulse(amplitude, T_0, T_e, T_ch, pulse_center, scan_range)
            if self._lf_parameters["rf_hsh_duration"] == None:
                segment = Segment("rf", duration=2*T_0 + T_ch)
            else:
                segment = Segment("rf", duration=self._lf_parameters["rf_hsh_duration"])
        else:
            pulse = AWGSineSweep(
                pulse_center - scan_range / 2,
                pulse_center + scan_range / 2,
                amplitude,
                start_time=0*ureg.s,
                end_time=T_ch,
            )
            segment = Segment("rf")
        segment.add_awg_function(rf_channel, pulse)
        self.add_segment(segment)

    def get_rf_sequence(self):
        segment_steps = []
        if self._rf_parameters["pre_lf"]:
            segment_steps.append(("rf", 1))
        segment_steps.append(("lf", 1))
        segment_steps.append(("rf", 1))
        if self._shutter_off_after_antihole:
            segment_steps.append(("shutter_break", self._shutter_rise_delay_repeats))
        detect_cycles = self._detect_parameters["cycles"]["rf"]
        segment_steps.extend(self.get_detect_sequence(detect_cycles))
        self.analysis_parameters["detect_groups"].append(("rf", detect_cycles))
        segment_steps.append(("break", 1))
        segment_steps.append(("break", self._shutter_fall_delay_repeats))
        return segment_steps
