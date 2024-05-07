from typing import Any
from onix.sequences.sequence import (
    AWGHSHPulse,
    AWGSinePulse,
    Segment,
    TTLOn,
)
from onix.sequences.shared import SharedSequence
from onix.awg_maps import get_channel_from_name
import numpy as np


class LFSpectroscopy(SharedSequence):
    """
    Use LF coil to drive b, b bar transition, the use HSH Pulse to drive either b to a or b bar to a transition
    HSH  https://doi.org/10.1364/AO.50.006548
    Parameters:
    "rf": {
        "amplitude": rabi frequency of transition, 
        "T_0": time at which to start frequency chirping,
        "T_e": width of edge function,
        "T_ch": time spent chirping,
        "center_frequency": center frequency of transition to drive,
        "scan_range": scan range we wish to go over
        }
    "lf": {
        "center_frequency": ,
        "detuning": , 
        "duration": ,
        "amplitude": ,
    }
    
    """
    def __init__(self, parameters: dict[str, Any]):
        super().__init__(parameters, shutter_off_after_antihole=False)
        self._lf_parameters = parameters["lf"]
        self._define_lf()
        self._define_rf()

    def _define_lf(self):
        lf_channel = get_channel_from_name(self._lf_parameters["name"])
        center_frequency =  self._lf_parameters["center_frequency"]
        detuning = self._lf_parameters["detuning"]
        duration = self._lf_parameters["duration"]
        amplitude = self._lf_parameters["amplitude"]
        segment = Segment("lf", duration=duration)
        pulse = AWGSinePulse(center_frequency + detuning, amplitude)
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
        center_frequency = self._rf_parameters["center_frequency"]
        scan_range = self._rf_parameters["scan_range"]
        pulse = AWGHSHPulse(amplitude, T_0, T_e, T_ch, center_frequency, scan_range)

        segment = Segment("rf", duration=2*T_0 + T_ch)
        segment.add_awg_function(rf_channel, pulse)
        self.add_segment(segment)

    def get_rf_sequence(self):
        # the shutter is open (high) at the beginning of this function.
        segment_steps = []
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
