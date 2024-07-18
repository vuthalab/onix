from typing import Any
from onix.sequences.sequence import (
    AWGCompositePulse,
    AWGConstant,
    AWGHSHPulse,
    AWGSinePulse,
    Segment,
    SegmentEmpty,
    Sequence,
    TTLOn,
)
import numpy as np
from onix.models.hyperfine import energies
from onix.sequences.shared import detect_segment
from onix.awg_maps import get_channel_from_name
from onix.units import ureg


class LFSpectroscopyQuickStatePrep(Sequence):
    def __init__(self, parameters: dict[str, Any]):
        parameters["eos"] = None
        parameters["field_plate"]["during"] = {
            "chasm": False,
            "antihole": False,
            "rf": False,
            "lf": False,
            "detect": True,
        }
        super().__init__()
        self._ao_parameters = parameters["ao"]
        self._field_plate_parameters = parameters["field_plate"]
        self._shutter_parameters = parameters["shutter"]
        self._optical_parameters = parameters["optical"]
        self._rf_parameters = parameters["rf"]
        self._rf_pump_parameters = parameters["rf_pump"]
        self._detect_parameters = parameters["detect"]
        self._lf_parameters = parameters["lf"]
        self._sequence_parameters = parameters["sequence"]
        self._define_optical()
        self._define_detect()
        self._define_rf()
        self._define_breaks()
        self._define_lf()
        #self._define_lf_sweep()

    def _define_optical(self):
        optical_sequence_duration = 1 * ureg.ms
        ao_channel = get_channel_from_name(self._ao_parameters["name"])
        amplitude = self._optical_parameters["ao_amplitude"]
        detuning_ac = 0 * ureg.MHz
        frequency_ac = self._ao_parameters["center_frequency"] + (
            detuning_ac / self._ao_parameters["order"]
        )
        segment = Segment("optical_ac", duration=optical_sequence_duration)
        pulse = AWGSinePulse(frequency_ac, amplitude)
        segment.add_awg_function(ao_channel, pulse)
        self.add_segment(segment)

        detuning_cb = -18 * ureg.MHz
        frequency_cb = self._ao_parameters["center_frequency"] + (
            detuning_cb / self._ao_parameters["order"]
        )
        segment = Segment("optical_cb", duration=optical_sequence_duration)
        pulse = AWGSinePulse(frequency_cb, amplitude)
        segment.add_awg_function(ao_channel, pulse)
        self.add_segment(segment)

    def _define_detect(self):
        segment, self.analysis_parameters = detect_segment(
            "detect",
            self._ao_parameters,
            None,
            self._field_plate_parameters,
            self._shutter_parameters,
            self._detect_parameters,
        )
        self.analysis_parameters["detect_groups"] = []
        self.add_segment(segment)

        if self._field_plate_parameters["use"]:
            field_plate_opposite = self._field_plate_parameters.copy()
            field_plate_opposite["amplitude"] = -field_plate_opposite["amplitude"]
            segment, self.analysis_parameters = detect_segment(
                "detect_opposite",
                self._ao_parameters,
                None,
                field_plate_opposite,
                self._shutter_parameters,
                self._detect_parameters,
            )
            self.analysis_parameters["detect_groups"] = []
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
        scan_range = self._rf_parameters["scan_range"]

        abar_bbar_detuning = -57 * ureg.kHz
        pulse_center_abar_bbar = center_frequency + self._rf_parameters["offset"] + abar_bbar_detuning
        segment = Segment("rf_abar_bbar", duration=2*T_0 + T_ch)
        pulse = AWGHSHPulse(amplitude, T_0, T_e, T_ch, pulse_center_abar_bbar, scan_range)
        segment.add_awg_function(rf_channel, pulse)
        self.add_segment(segment)

        a_b_detuning = 53 * ureg.kHz
        pulse_center_a_b = center_frequency + self._rf_parameters["offset"] + a_b_detuning
        segment = Segment("rf_a_b", duration=2*T_0 + T_ch)
        pulse = AWGHSHPulse(amplitude, T_0, T_e, T_ch, pulse_center_a_b, scan_range)
        segment.add_awg_function(rf_channel, pulse)
        self.add_segment(segment)

    def _define_lf(self):
        lf_channel = get_channel_from_name(self._lf_parameters["name"])
        center_frequencies =  self._lf_parameters["center_frequencies"]
        amplitudes =  self._lf_parameters["amplitudes"]
        detunings = self._lf_parameters["detunings"]
        durations = self._lf_parameters["durations"]
        phase_diffs = self._lf_parameters["phase_diffs"]
        wait_times = self._lf_parameters["wait_times"]
        for kk in range(len(detunings)):
            center_frequency = center_frequencies[kk]
            detuning = detunings[kk]
            duration = durations[kk]
            amplitude = amplitudes[kk]
            phase_diff = phase_diffs[kk]
            wait_time = wait_times[kk]
            if wait_time <= 0 * ureg.s:
                segment = Segment(f"lf_{kk}", duration=duration)
                pulse = AWGSinePulse(center_frequency + detuning, amplitude)
                segment.add_awg_function(lf_channel, pulse)
            else:
                segment = Segment(f"lf_{kk}")
                wait_in_piov2 = (wait_time / duration).to("").magnitude
                pulse = AWGCompositePulse(
                    np.array([1, wait_in_piov2, 1]) * duration,
                    center_frequency + detuning,
                    np.array([amplitude, 0, amplitude]),
                    np.array([0, 0, phase_diff]),
                )
                segment.add_awg_function(lf_channel, pulse)
            self.add_segment(segment)

    def _define_breaks(self):
        break_time = 10 * ureg.us
        segment = SegmentEmpty("break", break_time)
        self.add_segment(segment)

        segment = Segment("shutter_break", break_time)
        segment.add_ttl_function(self._shutter_parameters["channel"], TTLOn())
        self.add_segment(segment)
        if self._field_plate_parameters["use"]:
            segment.add_awg_function(
                get_channel_from_name(self._field_plate_parameters["name"]),
                AWGConstant(self._field_plate_parameters["amplitude"])
            )

            segment = Segment("shutter_break_opposite", break_time)
            segment.add_ttl_function(self._shutter_parameters["channel"], TTLOn())
            self.add_segment(segment)
            segment.add_awg_function(
                get_channel_from_name(self._field_plate_parameters["name"]),
                AWGConstant(-self._field_plate_parameters["amplitude"])
            )

        self._shutter_rise_delay_repeats = int(
            self._shutter_parameters["rise_delay"] / break_time
        )
        self._shutter_fall_delay_repeats = int(
            self._shutter_parameters["fall_delay"] / break_time
        )

    def setup_sequence(self):
        segment_steps = []
        for name, repeats in self._sequence_parameters["sequence"]:
            if name.startswith("detect"):
                if "opposite" in name:
                    segment_steps.append(("shutter_break_opposite", self._shutter_rise_delay_repeats))
                    segment_steps.append(("detect_opposite", repeats))
                else:
                    segment_steps.append(("shutter_break", self._shutter_rise_delay_repeats))
                    segment_steps.append(("detect", repeats))
                segment_steps.append(("break", self._shutter_fall_delay_repeats))
                analysis_name = name.split("_")[-1]
                self._detect_parameters["cycles"][analysis_name] = repeats
                self.analysis_parameters["detect_groups"].append((analysis_name, repeats))
            else:
                segment_steps.append((name, repeats))
            segment_steps.append(("break", 1))
        return super().setup_sequence(segment_steps)

    def num_of_record_cycles(self):
        total_cycles = 0
        for name, cycles in self.analysis_parameters["detect_groups"]:
            total_cycles += cycles
        return total_cycles
