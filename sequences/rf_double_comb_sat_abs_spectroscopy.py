from typing import Any

from onix.models.hyperfine import energies
from onix.sequences.sequence import (
    AWGDoubleSineTrain,
    Segment,
    TTLOn,
)
from onix.sequences.shared import SharedSequence
from onix.units import ureg
from onix.awg_maps import get_channel_from_name


class RFDoubleCombSatAbsSpectroscopy(SharedSequence):
    def __init__(self, parameters: dict[str, Any]):
        super().__init__(parameters, shutter_off_after_antihole=False)
        self._define_rf()
        
    def _define_rf(self):
        rf_channel = get_channel_from_name(self._rf_parameters["name"])
        lower_state = self._rf_parameters["transition"][0]
        upper_state = self._rf_parameters["transition"][1]
        offset = self._rf_parameters["offset"]
        center_frequency = energies["7F0"][upper_state] - energies["7F0"][lower_state] + offset

        pump_detunings = self._rf_parameters["pump_detunings"]
        pump_freqs = center_frequency + pump_detunings
        pump_time = self._rf_parameters["pump_time"]
        pump_amplitude = self._rf_parameters["pump_amplitude"]

        probe_detuning = self._rf_parameters["probe_detuning"]
        probe_freqs = pump_freqs + probe_detuning
        probe_time = self._rf_parameters["probe_time"]
        probe_amplitude = self._rf_parameters["probe_amplitude"]
        probe_phase = self._rf_parameters["probe_phase"]

        delay_time = self._rf_parameters["delay_time"]
        
        segment = Segment("rf") # TODO: include duration here
        segment.add_awg_function(
            rf_channel, 
            AWGDoubleSineTrain(
                pump_freqs,
                pump_amplitude,
                pump_time,
                0,
                delay_time,
                probe_freqs,
                probe_amplitude,
                probe_time,
                0,
                probe_phase,
            ),
        )
        if not self._shutter_off_after_antihole:
            segment.add_ttl_function(self._shutter_parameters["channel"], TTLOn())
        self.add_segment(segment)

    def get_rf_sequence(self):
        # the shutter is open (high) at the beginning of this function.
        segment_steps = []
        segment_steps.append(("rf", 1))
        if self._shutter_off_after_antihole:
            segment_steps.append(("shutter_break", self._shutter_rise_delay_repeats))
        detect_cycles = self._detect_parameters["cycles"]["rf"]
        segment_steps.append(("detect", detect_cycles))
        self.analysis_parameters["detect_groups"].append(("rf", detect_cycles))
        segment_steps.append(("break", 1))
        segment_steps.append(("break", self._shutter_fall_delay_repeats))
        return segment_steps
