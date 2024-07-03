from typing import Any
from onix.sequences.sequence import (
    AWGCompositePulse,
    AWGHSHPulse,
    AWGSinePulse,
    AWGSineSweep,
    AWGSineTrain,
    MultiSegments,
    AWGConstant,
    Segment,
    TTLOn,
)
import numpy as np
from onix.models.hyperfine import energies
from onix.sequences.shared import SharedSequence, _rf_pump_segment, _scan_segment, chasm_segment
from onix.awg_maps import get_channel_from_name
from onix.units import ureg


class LFSpectroscopyHole(SharedSequence):
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
        parameters["eos"] = None
        super().__init__(parameters, shutter_off_after_antihole=True)
        self._lf_parameters = parameters["lf"]
        #self._define_lf1()
        self._define_rf()
        self._define_lf()

    def _define_lf1(self):
        lf_channel = get_channel_from_name(self._rf_parameters["name"])
        center_frequency =  self._lf_parameters["center_frequency"]
        duration = self._lf_parameters["duration"]
        amplitude = self._lf_parameters["amplitude"]

        segment = Segment("lf1")
        composite_piov2 = AWGCompositePulse(
            np.array([1]) * duration,
            center_frequency,
            amplitude,
            np.array([0]),
        )
        segment.add_awg_function(lf_channel, composite_piov2)
        if not self._shutter_off_after_antihole:
            segment.add_ttl_function(self._shutter_parameters["channel"], TTLOn())
        self.add_segment(segment)

    def _define_lf(self):
        lf_channel = get_channel_from_name(self._rf_parameters["name"])
        center_frequency =  self._lf_parameters["center_frequency"]
        detuning = self._lf_parameters["detuning"]
        duration = self._lf_parameters["duration"]
        amplitude = self._lf_parameters["amplitude"]
        if "wait_time" not in self._lf_parameters or self._lf_parameters["wait_time"] <= 0 * ureg.s:
            segment = Segment("lf", duration=duration)
            # pulse = AWGSineSweepEnveloped(center_frequency + detuning, center_frequency + detuning, amplitude, 0, duration)
            pulse = AWGSinePulse(center_frequency + detuning, amplitude)
            segment.add_awg_function(lf_channel, pulse)
        else:
            segment = Segment("lf")
            pulse = AWGSineTrain(duration, self._lf_parameters["wait_time"], center_frequency + detuning, amplitude, [0, self._lf_parameters["phase_diff"]])
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

        # pulse_center = self._rf_parameters["center_detuning2"] + center_frequency
        # scan_range = self._rf_parameters["scan_range"]
        # if self._rf_parameters["use_hsh"]:
        #     pulse = AWGHSHPulse(amplitude, T_0, T_e, T_ch, pulse_center, scan_range)
        #     if self._lf_parameters["rf_hsh_duration"] == None:
        #         segment = Segment("rf1", duration=2*T_0 + T_ch)
        #     else:
        #         segment = Segment("rf1", duration=self._lf_parameters["rf_hsh_duration"])
        # else:
        #     pulse = AWGSineSweep(
        #         pulse_center - scan_range / 2,
        #         pulse_center + scan_range / 2,
        #         amplitude,
        #         start_time=0*ureg.s,
        #         end_time=T_ch,
        #     )
        #     segment = Segment("rf1")
        # segment.add_awg_function(rf_channel, pulse)
        # self.add_segment(segment)


    def get_rf_sequence(self):
        segment_steps = []

        if self._rf_parameters["pre_lf"]:
            segment_steps.append(("rf", 1))
            segment_steps.append(("break", 1))

        segment_steps.append(("lf", 1)) # pi/2 b <-> bbar

        segment_steps.append(("rf", 1)) # pi a <-> b

        segment_steps.append(("break", 1))
        segment_steps.append(("shutter_break", int(self._rf_parameters["cool_down_time"] / (10 * ureg.us))))
        if self._shutter_off_after_antihole:
            segment_steps.append(("shutter_break", self._shutter_rise_delay_repeats))
        detect_cycles = self._detect_parameters["cycles"]["rf"]
        segment_steps.extend(self.get_detect_sequence(detect_cycles))
        self.analysis_parameters["detect_groups"].append(("rf", detect_cycles))
        segment_steps.append(("break", 1))
        segment_steps.append(("break", self._shutter_fall_delay_repeats))

        # segment_steps.append(("lf", 1)) # ramsey sequence b <-> bbar

        # segment_steps.append(("rf1", 1)) # pi abar <-> bbar

        # segment_steps.append(("break", 1))
        # segment_steps.append(("shutter_break", int(self._rf_parameters["cool_down_time"] / (10 * ureg.us))))
        # if self._shutter_off_after_antihole:
        #     segment_steps.append(("shutter_break", self._shutter_rise_delay_repeats))
        # detect_cycles = self._detect_parameters["cycles"]["lf"]
        # segment_steps.extend(self.get_detect_sequence(detect_cycles))
        # self.analysis_parameters["detect_groups"].append(("lf", detect_cycles))
        # segment_steps.append(("break", 1))
        # segment_steps.append(("break", self._shutter_fall_delay_repeats))

        return segment_steps
