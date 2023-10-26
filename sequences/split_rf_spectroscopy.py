from typing import Dict

import numpy as np

from onix.sequences.sequence import (
    AWGSineTrain,
    Sequence,
    Segment,
    SegmentEmpty,
    AWGSinePulse,
    AWGSineSweep,
    TTLOff,
    TTLOn,
)
from onix.sequences.shared import scan_segment, detect_segment
from onix.models.hyperfine import energies
from onix.units import Q_, ureg


class SplitRFSpectroscopy(Sequence):
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
        field_plate_channel: int,
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
        self._field_plate_channel = field_plate_channel
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
            None,
            1 * ureg.s,
            0 * ureg.Hz,
            0 * ureg.Hz,
        )
        segment.add_ttl_function(self._field_plate_channel, TTLOff())
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
        segment.add_ttl_function(self._field_plate_channel, TTLOff())
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
            segment.add_ttl_function(self._field_plate_channel, TTLOff())
            self.add_segment(segment)

    def _add_flop(self):
        lower_state = self._flop_parameters["transition"][0]
        upper_state = self._flop_parameters["transition"][1]
        frequency = energies["7F0"][upper_state] - energies["7F0"][lower_state] + self._flop_parameters["offset"]
        print("flop", round(frequency, 2))
        lower = (frequency - self._flop_parameters["scan"]).to("Hz").magnitude
        upper = (frequency + self._flop_parameters["scan"]).to("Hz").magnitude
        step = self._flop_parameters["step_frequency"].to("Hz").magnitude
        scan_frequencies = np.arange(lower, upper, step) * ureg.Hz
        step_time = self._flop_parameters["step_time"]
        on_time = self._flop_parameters["on_time"]
        off_time = step_time - on_time
        if off_time < 0 * ureg.s:
            raise ValueError("step time must be longer than on time.")
        max_segment_duration = 40 * ureg.ms
        steps_per_segment = int((max_segment_duration / step_time).to("").magnitude)
        self._flop_segments = int(((len(scan_frequencies) - 1) / steps_per_segment)) + 1

        for kk in range(self._flop_segments):
            start_index = steps_per_segment * kk
            end_index = steps_per_segment * (kk + 1) - 1
            name = f"flop_{self._flop_parameters['transition']}_{kk}"
            segment = Segment(name)
            rf_pulse = AWGSineTrain(
                on_time,
                off_time,
                scan_frequencies[start_index:end_index+1],
                self._flop_parameters["amplitude"],
            )
            segment.add_awg_function(self._rf_channel, rf_pulse)
            segment.add_ttl_function(self._field_plate_channel, TTLOn())
            self.add_segment(segment)

    def _add_detect(self):
        segment, self.detect_time = detect_segment(
            f"detect_{self._detect_parameters['transition']}",
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
        segment.add_ttl_function(self._field_plate_channel, TTLOff())
        self.add_segment(segment)

    def _add_break(self, break_time: Q_ = 10 * ureg.us):
        segment = SegmentEmpty("break", break_time)
        segment.add_ttl_function(self._field_plate_channel, TTLOff())
        self.add_segment(segment)
        delay_segment_time = 1 * ureg.ms
        self._delay_repeats = int(self._detect_parameters["delay_time"] / delay_segment_time)
        delay = SegmentEmpty("delay", delay_segment_time)
        segment.add_ttl_function(self._field_plate_channel, TTLOff())
        self.add_segment(delay)
        delay_with_field_plate_on = SegmentEmpty("delay_with_field_plate_on", delay_segment_time)
        segment.add_ttl_function(self._field_plate_channel, TTLOn())
        self.add_segment(delay_with_field_plate_on)

    def setup_sequence(self):
        detect_repeats = self._detect_parameters["repeats"]
        detect_name = f"detect_{self._detect_parameters['transition']}"

        segment_repeats = []
        segment_repeats.append(("carrier_burn", self._carrier_burn_repeats))
        segment_repeats.append(("break", 1))
        segment_repeats.append(("delay", self._delay_repeats))
        segment_repeats.append((detect_name, detect_repeats))
        segment_repeats.append(("break", 1))

        segment_repeats.append((
            f"burn_{self._burn_parameters['transition']}",
            self._burn_repeats,
        ))
        segment_repeats.append(("break", 1))
        segment_repeats.append(("delay", self._delay_repeats))
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
        segment_repeats.append(("delay", self._delay_repeats))
        segment_repeats.append((detect_name, detect_repeats))
        segment_repeats.append(("break", 1))

        segment_repeats.append(("delay_with_field_plate_on", 10))
        for kk in range(self._flop_segments):
            segment_repeats.append((f"flop_{self._flop_parameters['transition']}_{kk}", self._flop_parameters["repeats"]))
        segment_repeats.append(("break", 1))
        segment_repeats.append(("delay", self._delay_repeats))
        segment_repeats.append((detect_name, detect_repeats))
        return super().setup_sequence(segment_repeats)

    def num_of_records(self) -> int:
        return 4 * self._detect_parameters["repeats"]
