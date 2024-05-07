from typing import Any
from functools import partial

from onix.models.hyperfine import energies, states
from onix.sequences.sequence import (
    AWGHSHPulse,
    AWGSinePulse,
    Segment,
    TTLOn,
)
from onix.sequences.shared import SharedSequence
from onix.units import ureg
from onix.awg_maps import get_channel_from_name
import numpy as np


class LFSpectroscopy(SharedSequence):
    """
    Use LF coil to drive b, b bar transition, the use HSH Pulse to drive either b to a or b bar to a transition
    HSH  https://doi.org/10.1364/AO.50.006548
    Parameters:
    rf: {
        "duration": time for entire HSH pulse, 
        "Omega": rabi frequency of transition, 
        "t_0": time at which to start frequency chirping,
        "T_e": width of edge function,
        "T_ch": chirp time,
        "frequency": frequency of transition to drive,
        "kappa": linear chip rate,
        }
    lf: {
        "frequency": ,
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
        # turn on the lf coil at some frequency, power, duration to drive b, b bar transition
        lf_channel = get_channel_from_name(self._lf_parameters["name"])
        frequency =  self._lf_parameters["frequency"]
        detuning = self._lf_parameters["detuning"]
        duration = self._lf_parameters["duration"]
        amplitude = self._lf_parameters["amplitude"]
        segment = Segment("lf", duration=duration)
        pulse = AWGSinePulse(frequency + detuning, amplitude)
        segment.add_awg_function(lf_channel, pulse)
        if not self._shutter_off_after_antihole:
            segment.add_ttl_function(self._shutter_parameters["channel"], TTLOn())
        self.add_segment(segment)


    def _define_rf(self):
        rf_channel = get_channel_from_name(self._rf_parameters["name"])
        duration = self._rf_parameters["duration"]
        Omega = self._rf_parameters["Omega"]
        t_0 = self._rf_parameters["t_0"]
        T_e = self._rf_parameters["T_e"]
        T_ch = self._rf_parameters["T_ch"]
        omega_0 = self._rf_parameters["frequency"] * 2 * np.pi
        kappa = self._rf_parameters["kappa"]
        pulse = AWGHSHPulse(duration, Omega, t_0, T_e, T_ch, omega_0, kappa)

        segment = Segment("rf", duration=duration)
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
