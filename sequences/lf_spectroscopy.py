from typing import Any
from functools import partial

from onix.models.hyperfine import energies, states
from onix.sequences.sequence import (
    AWGConstant,
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
    Additional Parameters:
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
        """
        Parameters:
        rf: {
        "duration": time for entire HSH pulse, 
        "Omega": rabi frequency of transition, 
        "t0": time at which to start frequency chirping,
        "T_e": width of edge function,
        "T_ch": chirp time,
        "frequency": frequency of transition to drive,
        "kappa": linear chip rate,
        }
        
        """
        rf_channel = get_channel_from_name(self._rf_parameters["name"])

        #parameters to run a HSH pulse
        duration = self._rf_parameters["duration"]
        Omega_ch = self._rf_parameters["Omega"]
        t0 = self._rf_parameters["t0"]
        T_e = self._rf_parameters["T_e"]
        T_ch = self._rf_parameters["T_ch"]
        omega_0 = self._rf_parameters["frequency"] * 2 * np.pi
        kappa = self._rf_parameters["kappa"]

        sample_rate_awg = 625e6 #Hz
        dt = 1/sample_rate_awg
        t = np.linspace(0, duration, sample_rate_awg * duration)
        condlist = [np.where(t < t0), 
                    np.logical_and(np.where(t >= t0), np.where(t <= t0+T_ch)), 
                    np.where(t > t0+T_ch)]
        
        funclist_amplitudes = [lambda t: Omega_ch/np.cosh((t - t0)/T_e),
                               lambda t: Omega_ch,
                               lambda t: Omega_ch/np.cosh((t - t0 - T_ch)/T_e)]
        
        funclist_frequencies = [lambda t: omega_0 - kappa*T_ch/2 + kappa*T_e*np.tanh((t - t0)/T_e),
                               lambda t: omega_0 - kappa*(t - t0 - T_ch/2),
                               lambda t: omega_0 + kappa*T_ch/2 + kappa*T_e*np.tanh((t - t0 - T_ch)/T_e)]
        

        # create sine wave with this evelope and frequencies
        instant_amplitudes = np.piecewise(t, condlist, funclist_amplitudes)
        instant_frequencies = np.piecewise(t, condlist, funclist_frequencies)
        phases = np.array([np.sum(instant_frequencies[0:n])*dt for n in range(instant_frequencies.size)])

        pulse = instant_amplitudes * np.sin(
            2 * np.pi * instant_frequencies * t + phases
        )

        segment = Segment("rf", duration=duration)
        
        segment.add_awg_function(rf_channel, pulse)
        if not self._shutter_off_after_antihole:
            segment.add_ttl_function(self._shutter_parameters["channel"], TTLOn())
        self.add_segment(segment)

    """
    def _define_rf(self):
        # perform a HSH pulse to transfer population from either b or b bar into a
        rf_channel = get_channel_from_name(self._rf_parameters["name"])
        
        duration = self._rf_parameters["duration"]
        amplitude = self._rf_parameters["amplitude"]
        t0 = self._rf_parameters["t_0"]
        Omega_ch =  self._rf_parameters["Omega_ch"]
        sample_rate_awg = 625e6 #Hz

        t = np.linspace(0, duration, sample_rate_awg * duration)
        T_ch = duration - 2*t0
        T_e = 0
        kappa = 0
        omega_0 = 0

        def sine(frequency, amplitude, phase, times):
            return amplitude * np.sin(2 * np.pi * frequency * times + phase)

        condlist = [np.where(t < t0), 
                    np.logical_and(np.where(t >= t0), np.where(t <= t0+T_ch)), 
                    np.where(t > t0+T_ch)]
        
        funclist_amplitudes = [lambda t: Omega_ch/np.cosh((t - t0)/T_e),
                               lambda t: Omega_ch,
                               lambda t: Omega_ch/np.cosh((t - t0 - T_ch)/T_e)]
        
        funclist_frequencies = [lambda t: omega_0 - kappa*T_ch/2 + kappa*T_e*np.tanh((t - t0)/T_e),
                               lambda t: omega_0 - kappa*(t - t0 - T_ch/2),
                               lambda t: omega_0 + kappa*T_ch/2 + kappa*T_e*np.tanh((t - t0 - T_ch)/T_e)]
        

        # create sine wave with this evelope and frequencies
        amplitudes = np.piecewise(t, condlist, funclist_amplitudes)
        frequencies = np.piecewise(t, condlist, funclist_frequencies)
        pulse = partial(sine, amplitudes, frequencies)

        segment = Segment("rf", duration=duration)
        
        segment.add_awg_function(rf_channel, pulse)
        if not self._shutter_off_after_antihole:
            segment.add_ttl_function(self._shutter_parameters["channel"], TTLOn())
        self.add_segment(segment)
    """

    def get_rf_sequence(self):
        # the shutter is open (high) at the beginning of this function.
        segment_steps = []
        segment_steps.append(("rf", 1))
        if self._shutter_off_after_antihole:
            segment_steps.append(("shutter_break", self._shutter_rise_delay_repeats))
        detect_cycles = self._detect_parameters["cycles"]["rf"]
        segment_steps.extend(self.get_detect_sequence(detect_cycles))
        self.analysis_parameters["detect_groups"].append(("rf", detect_cycles))
        segment_steps.append(("break", 1))
        segment_steps.append(("break", self._shutter_fall_delay_repeats))
        return segment_steps
