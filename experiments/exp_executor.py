import numpy as np
import copy

from onix.sequences.sequence import Segment


name_to_segment_builder = {
    "chasm": chasm_segments,
    "antihole": antihole_segments,
    "detect": detect_segments,
    "rf_sweep": rf_sweep_segments,
    "lf_ramsey": lf_ramsey_segments,
    "lf_ramsey": lf_ramsey_segments,
    "lf_rabi": lf_rabi_segments,
    "lf_equilibrate": lf_equilibrate_segments,
}


class ExpExecutor:
    def __init__(self, exp_sequence, parameters, alternative_sequence_steps = None):
        self._exp_sequence = exp_sequence
        self._parameters = parameters
        if not alternative_sequence_steps:
            alternative_sequence_steps = {}
        self._alternative_sequence_steps = alternative_sequence_steps

        self._build_segments_and_steps()

    def _build_segments(self, sequence_step_name: str, parameters: dict):
        for match_name, segment_builder_func in name_to_segment_builder.items():
            return segment_builder_func(sequence_step_name[len(match_name):], parameters)

    def update_parameters_from_shared(self, parameters_overriden):
        parameters = copy.deepcopy(parameters_overriden)
        for kk in self._parameters:
            if kk in parameters:
                if isinstance(parameters[kk], dict):
                    parameters[kk] = self.update_parameters_from_shared(
                        parameters[kk], self._parameters[kk]
                    )
            else:
                parameters[kk] = self._parameters[kk]
        return parameters

    def _build_segments_and_steps(self):
        self._segment_and_steps: list[tuple[Segment, int]] = []
        for sequence_step in self._exp_sequence:
            segment = self._build_segments(sequence_step, self._parameters)
            self._segment_and_steps.extend(segment)
        for sequence_step, parameters_overriden in self._alternative_sequence_steps.items():
            parameters = self.update_parameters_from_shared(parameters_overriden)
            segment = self._build_segments(sequence_step, parameters)
            self._segment_and_steps.extend(segment)
    
    @property
    def segments(self):
        return list(set([segment for segment, steps in self._segment_and_steps]))

    @property
    def segment_steps(self):
        return [(segment.name, steps) for segment, steps in self._segment_and_steps]
