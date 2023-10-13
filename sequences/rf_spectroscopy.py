from typing import Dict

from onix.sequences.sequence import (
    Sequence,
    Segment,
    SegmentEmpty,
    AWGSinePulse,
)
from onix.sequences.shared import scan_segment, probe_segment
from onix.models.hyperfine import energies
from onix.units import Q_, ureg


class RFSpectroscopy(Sequence):
    def __init__(
        self,
        ao_parameters: Dict,
        eo_parameters: Dict,
        detect_ao_parameters: Dict,
        burn_parameters: Dict,
        repop_parameters: Dict,
        flop_parameters: Dict,
        detect_parameters: Dict,
        digitizer_channel: int,
        rf_channel: int,
    ):
        super().__init__()
        self._ao_parameters = ao_parameters
        self._eo_parameters = eo_parameters
        self._detect_ao_parameters = detect_ao_parameters
        self._burn_parameters = burn_parameters
        self._repop_parameters = repop_parameters
        self._flop_parameters = flop_parameters
        self._detect_parameters = detect_parameters
        self._digitizer_channel = digitizer_channel
        self._rf_channel = rf_channel
        self._add_carrier_burn()
        self._add_burn()
        self._add_repop()
        self._add_flop()
        self._add_detect()
        self._add_break()

    def _add_carrier_burn(self):
        segment, self._carrier_burn_repeats = scan_segment(
            "carrier_burn",
            self._ao_parameters,
            self._eo_parameters,
            1 * ureg.s,
            0 * ureg.Hz,
            -self._eo_parameters["offset"],
        )
        self.add_segment(segment)

    def _add_burn(self):
        segment, self._burn_repeats = scan_segment(
            f"burn_{self._burn_parameters['transition']}",
            self._ao_parameters,
            self._eo_parameters,
            self._burn_parameters["transition"],
            self._burn_parameters["duration"],
            self._burn_parameters["scan"],
            self._burn_parameters["detuning"],
        )
        self.add_segment(segment)

    def _add_repop(self):
        for kk in self._repop_parameters["transitions"]:
            segment, self._repop_repeats = scan_segment(
                f"repop_{kk}",
                self._ao_parameters,
                self._eo_parameters,
                kk,
                self._repop_parameters["duration"],
                self._repop_parameters["scan"],
                self._repop_parameters["detuning"],
            )
            self.add_segment(segment)

    def _add_flop(self):
        name = f"flop_{self._flop_parameters['transition']}"
        lower_state = self._flop_parameters["transition"][0]
        upper_state = self._flop_parameters["transition"][1]
        frequency = abs(energies["7F0"][upper_state] - energies["7F0"][lower_state]) + self._flop_parameters["offset"]
        print(name, round(frequency, 2))
        segment = Segment(name, self._flop_parameters["duration"])
        rf_pulse = AWGSinePulse(frequency, self._flop_parameters["amplitude"])
        segment.add_awg_function(self._rf_channel, rf_pulse)
        self.add_segment(segment)

    def _add_detect(self):
        segment, self.detect_time = scan_segment(
            f"burn_{self._detect_parameters['transition']}",
            self._ao_parameters,
            self._eo_parameters,
            self._detect_ao_parameters,
            self._digitizer_channel,
            self._detect_parameters["transition"],
            self._detect_parameters["detunings"],
            self._detect_parameters["on_time"],
            self._detect_parameters["off_time"],
            self._detect_parameters["ttl_detect_offset_time"],
            self._detect_parameters["ttl_start_time"],
            self._detect_parameters["ttl_duration"],
        )
        self.add_segment(segment)

    def _add_break(self, break_time: Q_ = 10 * ureg.us):
        segment = SegmentEmpty("break", break_time)
        self.add_segment(segment)

    def setup_sequence(self):
        detect_repeats = self._detect_parameters["repeats"]
        detect_name = f"detect_{self._detect_parameters['transition']}"

        segment_repeats = []
        segment_repeats.append(("carrier_burn", self._carrier_burn_repeats))
        segment_repeats.append(("break", 1))
        segment_repeats.append((detect_name, detect_repeats))
        segment_repeats.append(("break", 1))

        segment_repeats.append((
            f"burn_{self._burn_parameters['transition']}",
            self._burn_repeats,
        ))
        segment_repeats.append(("break", 1))
        segment_repeats.append((detect_name, detect_repeats))
        segment_repeats.append(("break", 1))

        if self._repop_repeats > 100:
            repop_segment_repeat = int(self._repop_repeats / 10)
            repop_loop_repeat = 10
        else:
            repop_segment_repeat = 1
            repop_loop_repeat = self._repop_repeats
        for kk in range(repop_loop_repeat):
            for name in self._repop_parameters["transitions"]:
                segment_repeats.append((f"repop_{name}", repop_segment_repeat))
        segment_repeats.append(("break", 1))
        segment_repeats.append((detect_name, detect_repeats))
        segment_repeats.append(("break", 1))

        segment_repeats.append(("flop", self._flop_parameters["repeats"]))
        segment_repeats.append(("break", 1))
        segment_repeats.append((detect_name, detect_repeats))
        return super().setup_sequence(segment_repeats)

    def num_of_records(self) -> int:
        return 4 * self._detect_parameters["repeats"]
