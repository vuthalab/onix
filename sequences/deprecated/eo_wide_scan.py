from typing import Dict

from onix.sequences.sequence import (
    AWGSineSweep,
    Sequence,
    Segment,
    SegmentEmpty,
    AWGSinePulse,
)
from onix.sequences.shared import scan_segment, detect_segment
from onix.models.hyperfine import energies
from onix.units import Q_, ureg


class EOWideScan(Sequence):
    def __init__(
        self,
        ao_parameters: Dict,
        eo_parameters: Dict,
        detect_ao_parameters: Dict,
        sweep_parameters: Dict,
        burn_parameters: Dict,
        burn1_parameters: Dict,
        flop_parameters: Dict,
        detect_parameters: Dict,
        digitizer_channel: int,
        rf_channel: int,
    ):
        super().__init__()
        self._ao_parameters = ao_parameters
        self._eo_parameters = eo_parameters
        self._detect_ao_parameters = detect_ao_parameters
        self._sweep_parameters = sweep_parameters
        self._burn_parameters = burn_parameters
        self._burn1_parameters = burn1_parameters
        self._flop_parameters = flop_parameters
        self._detect_parameters = detect_parameters
        self._digitizer_channel = digitizer_channel
        self._rf_channel = rf_channel
        self._add_sweep()
        self._add_carrier_burn()
        self._add_burn()
        self._add_burn1()
        self._add_flop()
        self._add_detect()
        self._add_break()

    def _add_sweep(self):
        segment, self._sweep_repeats = scan_segment(
            "sweep",
            self._ao_parameters,
            self._eo_parameters,
            None,
            self._sweep_parameters["duration"],
            self._sweep_parameters["scan"],
            0 * ureg.Hz,
        )
        self.add_segment(segment)


    def _add_carrier_burn(self):
        segment, self._carrier_burn_repeats = scan_segment(
            "carrier_burn",
            self._ao_parameters,
            self._eo_parameters,
            None,
            self._burn_parameters["duration"],
            0 * ureg.Hz,
            0 * ureg.Hz,
        )
        self.add_segment(segment)

    def _add_burn(self):
        segment, self._burn_repeats = scan_segment(
            "burn",
            self._ao_parameters,
            self._eo_parameters,
            None,
            self._burn_parameters["duration"],
            self._burn_parameters["scan"],
            self._burn_parameters["detuning"],
        )
        self.add_segment(segment)

    def _add_burn1(self):
        segment, self._burn_repeats = scan_segment(
            "burn1",
            self._ao_parameters,
            self._eo_parameters,
            None,
            self._burn1_parameters["duration"],
            self._burn1_parameters["scan"],
            self._burn1_parameters["detuning"],
        )
        self.add_segment(segment)

    def _add_flop(self):
        name = "flop"
        lower_state = self._flop_parameters["transition"][0]
        upper_state = self._flop_parameters["transition"][1]
        frequency = energies["7F0"][upper_state] - energies["7F0"][lower_state] + self._flop_parameters["offset"]
        lower = frequency - self._flop_parameters["scan"]
        upper = frequency + self._flop_parameters["scan"]
        print(name, round(frequency, 2))
        segment = Segment(name, self._flop_parameters["duration"])
        rf_pulse = AWGSineSweep(lower, upper, self._flop_parameters["amplitude"], 0, self._flop_parameters["duration"])
        segment.add_awg_function(self._rf_channel, rf_pulse)
        self.add_segment(segment)

    def _add_detect(self):
        segment, self.detect_time = detect_segment(
            "detect",
            self._ao_parameters,
            self._eo_parameters,
            self._detect_ao_parameters,
            self._digitizer_channel,
            None,
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
        detect_name = "detect"

        segment_repeats = []
        segment_repeats.append(("sweep", self._sweep_repeats))
        segment_repeats.append((detect_name, detect_repeats))
        segment_repeats.append(("break", 1))

        segment_repeats.append(("carrier_burn", self._carrier_burn_repeats))
        segment_repeats.append(("break", 1))
        segment_repeats.append((detect_name, detect_repeats))
        segment_repeats.append(("break", 1))

        segment_repeats.append((
            "burn",
            self._burn_repeats,
        ))
        segment_repeats.append(("break", 1))
        segment_repeats.append((detect_name, detect_repeats))
        segment_repeats.append(("break", 1))

        segment_repeats.append((
            "burn1",
            self._burn_repeats,
        ))
        segment_repeats.append(("break", 1))
        segment_repeats.append((detect_name, detect_repeats))
        segment_repeats.append(("break", 1))

        segment_repeats.append((
            "flop",
            self._flop_parameters["repeats"],
        ))
        segment_repeats.append(("break", 1))
        segment_repeats.append((detect_name, detect_repeats))
        return super().setup_sequence(segment_repeats)

    def num_of_records(self) -> int:
        return 5 * self._detect_parameters["repeats"]
