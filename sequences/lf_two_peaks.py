from typing import Any
from onix.sequences.sequence import (
    AWGCompositePulse,
    AWGConstant,
    AWGHSHPulse,
    AWGSinePulse,
    AWGTwoSinePulse,
    AWGSineSweep,
    Segment,
    SegmentEmpty,
    Sequence,
    TTLOn,
)
import numpy as np
from onix.models.hyperfine import energies
from onix.sequences.shared import detect_segment, chasm_segment
from onix.awg_maps import get_channel_from_name, get_ttl_channel_from_name
from onix.units import ureg

class LFTwoPeaks(Sequence):
    def __init__(self, parameters: dict[str, Any]):
        parameters["eos"] = None
        parameters["field_plate"]["during"] = {
            "chasm": False,
            "antihole": False,
            "rf": False,
            "lf": False,
            "detect": False,
        }
        super().__init__()
        self._ao_parameters = parameters["ao"]
        self._eos_parameters = parameters["eos"]
        self._chasm_parameters = parameters["chasm"]
        self._field_plate_parameters = parameters["field_plate"]
        self._shutter_parameters = parameters["shutter"]
        self._optical_parameters = parameters["optical"]
        self._rf_parameters = parameters["rf"]
        self._rf_pump_parameters = parameters["rf_pump"]
        self._detect_parameters = parameters["detect"]
        self._lf_parameters = parameters["lf"]
        self._sequence_parameters = parameters["sequence"]
        self._cleanout_parameters = parameters["cleanout"]
        self._define_chasm()
        self._define_optical()
        self._define_detect()
        self._define_rf()
        self._define_breaks()
        self._define_field_plate_trigger()
        self._define_lf_piov2()
        self._define_lf()

    def _define_chasm(self):
        ao_channel = get_channel_from_name(self._ao_parameters["name"])
        amplitude = self._chasm_parameters["ao_amplitude"]

        detuning_ac = 0 * ureg.MHz
        frequency_ac = self._ao_parameters["center_frequency"] + (
            detuning_ac / self._ao_parameters["order"]
        )
        scan_range = self._chasm_parameters["scan"]
        start_frequency = frequency_ac - scan_range/self._ao_parameters["order"]
        end_frequency = frequency_ac + scan_range/self._ao_parameters["order"]
        duration = self._chasm_parameters["durations"]
        segment = Segment("chasm", duration=duration)
        pulse = AWGSineSweep(start_frequency, end_frequency, amplitude, start_time = 0, end_time = duration)
        
        segment.add_awg_function(ao_channel, pulse)
        self.add_segment(segment)

    def _define_optical(self):
        optical_sequence_duration = 1 * ureg.ms
        ao_channel = get_channel_from_name(self._ao_parameters["name"])
        amplitude_ac = self._optical_parameters["ao_amplitude_ac"]
        amplitude_cb = self._optical_parameters["ao_amplitude_cb"]
        detuning_ac = 0 * ureg.MHz
        frequency_ac = self._ao_parameters["center_frequency"] + (
            detuning_ac / self._ao_parameters["order"]
        )
        segment = Segment("optical_ac", duration=optical_sequence_duration)
        pulse = AWGSinePulse(frequency_ac, amplitude_ac)
        segment.add_awg_function(ao_channel, pulse)
        self.add_segment(segment)


        detuning_cb = self._optical_parameters["cb_detuning"]
        frequency_cb = self._ao_parameters["center_frequency"] + (
            detuning_cb / self._ao_parameters["order"]
        )
        segment = Segment("optical_cb", duration=optical_sequence_duration)

        if self._optical_parameters["use_mirror_cb"]:
            detuning_cb_mirror = -18 * ureg.MHz
            frequency_cb_mirror = self._ao_parameters["center_frequency"] + (
                detuning_cb_mirror / self._ao_parameters["order"]
            )
            pulse = AWGTwoSinePulse(frequency_cb, frequency_cb_mirror, amplitude_cb) # /2
        else:
            pulse = AWGSinePulse(frequency_cb, amplitude_cb) # /2
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

    def _define_rf(self):
        lower_state = self._rf_parameters["transition"][0]
        upper_state = self._rf_parameters["transition"][1]
        offset = self._rf_parameters["offset"]
        center_frequency = energies["7F0"][upper_state] - energies["7F0"][lower_state] + offset
        rf_channel = get_channel_from_name(self._rf_parameters["name"])

        amplitude = self._rf_parameters["HSH"]["amplitude"]
        T_0 = self._rf_parameters["HSH"]["T_0"]
        T_e = self._rf_parameters["HSH"]["T_e"]
        T_ch = self._rf_parameters["HSH"]["T_ch"]
        scan_range = self._rf_parameters["HSH"]["scan_range"]

        abar_bbar_detuning = self._rf_parameters["detuning_abarbbar"]
        pulse_center_abar_bbar = center_frequency + abar_bbar_detuning
        segment = Segment("rf_abarbbar", duration=2*T_0 + T_ch)
        pulse = AWGHSHPulse(amplitude, T_0, T_e, T_ch, pulse_center_abar_bbar, scan_range)
        segment.add_awg_function(rf_channel, pulse)
        self.add_segment(segment)

        a_b_detuning = self._rf_parameters["detuning_ab"]
        pulse_center_a_b = center_frequency + a_b_detuning
        segment = Segment("rf_ab", duration=2*T_0 + T_ch)
        pulse = AWGHSHPulse(amplitude, T_0, T_e, T_ch, pulse_center_a_b, scan_range)
        segment.add_awg_function(rf_channel, pulse)
        self.add_segment(segment)

    def _define_lf(self):
        lf_channel = get_channel_from_name(self._lf_parameters["name"])
        center_frequency_1 = self._lf_parameters["center_frequency_1"]
        center_frequency_2 = self._lf_parameters["center_frequency_2"]

        amplitude_1 = self._lf_parameters["amplitude_1"]
        amplitude_2 = self._lf_parameters["amplitude_2"]
        detuning = self._lf_parameters["detuning"]
        piov2_time = self._lf_parameters["piov2_time"]
        wait_time = self._lf_parameters["wait_time"]
        phases = self._lf_parameters["phase_diffs"]

        center_frequencies = [center_frequency_1, center_frequency_2]
        amplitudes = [amplitude_1, amplitude_2]
        for ll in range(len(center_frequencies)):
            for kk in range(len(phases)):
                phase = phases[kk]
                segment = Segment(f"lf_{kk + ll * len(phases)}")
                pulse = AWGCompositePulse(
                    [piov2_time, wait_time, piov2_time],
                    center_frequencies[ll] + detuning,
                    np.array([amplitudes[ll], 0, amplitudes[ll]]),
                    np.array([0, 0, phase]),
                )
                segment.add_awg_function(lf_channel, pulse)
                self.add_segment(segment)

    def _define_lf_piov2(self):
        lf_channel = get_channel_from_name(self._lf_parameters["name"])
        center_frequency_1 = self._lf_parameters["center_frequency_1"]
        center_frequency_2 = self._lf_parameters["center_frequency_2"]

        detuning = self._lf_parameters["detuning"]
        piov2_time = self._lf_parameters["equilibrate_piov2_time"]
        amplitude_1 = self._lf_parameters["equilibrate_amplitude_1"]
        amplitude_2 = self._lf_parameters["equilibrate_amplitude_2"]

        center_frequencies = [center_frequency_1, center_frequency_2]
        amplitudes = [amplitude_1, amplitude_2]
        for ll in range(len(center_frequencies)):
            segment = Segment(f"lfpiov2_{ll}")
            piov2_freq = center_frequencies[ll] + detuning
            pulse = AWGCompositePulse(
                [piov2_time * 119 / 90, piov2_time * 183 / 90, piov2_time * 211 / 90, piov2_time * 384 / 90, piov2_time * 211 / 90, piov2_time * 183 / 90, piov2_time * 119 / 90],
                [piov2_freq] * 7,
                [amplitudes[ll]] * 7,
                [np.pi, 0, np.pi, 0, np.pi, 0, np.pi],
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

        self._shutter_rise_delay_repeats = int(
            self._shutter_parameters["rise_delay"] / break_time
        )
        self._shutter_fall_delay_repeats = int(
            self._shutter_parameters["fall_delay"] / break_time
        )

    def _define_field_plate_trigger(self):
        segment = Segment("field_plate_trigger", 50 * ureg.us)
        fp_channel = get_ttl_channel_from_name(self._field_plate_parameters["name"])
        segment.add_ttl_function(fp_channel, TTLOn())
        self.add_segment(segment)

    def setup_sequence(self):
        segment_steps = []
        self.analysis_parameters["detect_groups"] = []
        self._detect_parameters["cycles"] = {}
        for name, repeats in self._sequence_parameters["sequence"]:
            if name.startswith("detect"):
                segment_steps.append(("shutter_break", self._shutter_rise_delay_repeats))
                segment_steps.append(("detect", repeats))
                segment_steps.append(("break", self._shutter_fall_delay_repeats))
                analysis_name = name.split("_")[-1]
                self._detect_parameters["cycles"][analysis_name] = repeats
                self.analysis_parameters["detect_groups"].append((analysis_name, repeats))
                self.field_plate_on_time = (
                    self._segments["shutter_break"].duration * self._shutter_rise_delay_repeats 
                    + self._segments["detect"].duration * repeats
                )
            else:
                if name.startswith("lf_"):
                    lf_index = int(name[3:])
                    if lf_index < len(self._lf_parameters["phase_diffs"]):
                        self._lf_parameters["center_frequency"] = self._lf_parameters["center_frequency_1"]
                        self._lf_parameters["amplitude"] = self._lf_parameters["amplitude_1"]
                        self._lf_parameters["equilibrate_amplitude"] = self._lf_parameters["equilibrate_amplitude_1"]
                    else:
                        self._lf_parameters["center_frequency"] = self._lf_parameters["center_frequency_2"]
                        self._lf_parameters["amplitude"] = self._lf_parameters["amplitude_2"]
                        self._lf_parameters["equilibrate_amplitude"] = self._lf_parameters["equilibrate_amplitude_2"]
                segment_steps.append((name, repeats))
            segment_steps.append(("break", 1))
        return super().setup_sequence(segment_steps)

    def num_of_record_cycles(self):
        total_cycles = 0
        for name, cycles in self.analysis_parameters["detect_groups"]:
            total_cycles += cycles
        return total_cycles
