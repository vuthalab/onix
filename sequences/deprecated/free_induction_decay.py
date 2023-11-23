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
    TTLPulses,
)
from onix.sequences.shared import scan_segment, detect_segment
from onix.models.hyperfine import energies
from onix.units import Q_, ureg


class FreeInductionDecay(Sequence):
    def __init__(
        self,
        ao_parameters: Dict,
        eo_parameters: Dict,
        detect_ao_parameters: Dict,
        burn_parameters: Dict,
        repop_parameters: Dict,
        pump_parameters: Dict,
        probe_parameters: Dict,
        digitizer_channel: int,
        field_plate_channel: int,
    ):
        super().__init__()
        self._ao_parameters = ao_parameters
        self._eo_parameters = eo_parameters
        self._detect_ao_parameters = detect_ao_parameters
        self._burn_parameters = burn_parameters
        self._repop_parameters = repop_parameters
        self._pump_parameters = pump_parameters
        self._probe_parameters = probe_parameters
        self._digitizer_channel = digitizer_channel
        self._field_plate_channel = field_plate_channel
        self._add_carrier_burn()
        self._add_burn()
        self._add_repop()
        self._add_pump_and_probe()
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
        segment.add_ttl_function(self._field_plate_channel, TTLOn())
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
        segment.add_ttl_function(self._field_plate_channel, TTLOn())
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
            segment.add_ttl_function(self._field_plate_channel, TTLOn())
            self.add_segment(segment)

    def _add_pump_and_probe(self):
        lower_state = self._pump_parameters["transition"][0]
        upper_state = self._pump_parameters["transition"][1]
        pump = Segment("pump", self._pump_parameters["time"])
        pump_frequency = (
            energies["5D0"][upper_state]
            - energies["7F0"][lower_state]
            + self._eo_parameters["offset"]
        )
        pump_ao_pulse = AWGSinePulse(
            self._ao_parameters["frequency"],
            self._pump_parameters["ao_amplitude"],
        )
        pump.add_awg_function(self._ao_parameters["channel"], pump_ao_pulse)
        pump_eo_pulse = AWGSinePulse(
            pump_frequency,
            self._eo_parameters["amplitude"]
        )
        pump.add_awg_function(self._eo_parameters["channel"], pump_eo_pulse)
        pump.add_ttl_function(self._field_plate_channel, TTLOn())
        self.add_segment(pump)

        probe = Segment("probe", self._probe_parameters["time"])
        probe_frequency = pump_frequency + self._probe_parameters["detuning"]
        probe_ao_pulse = AWGSinePulse(
            self._ao_parameters["frequency"],
            self._probe_parameters["ao_amplitude"],
        )
        probe.add_awg_function(self._ao_parameters["channel"], probe_ao_pulse)
        probe_eo_pulse = AWGSinePulse(
            probe_frequency,
            self._eo_parameters["amplitude"],
            self._probe_parameters["phase"],
        )
        probe.add_awg_function(self._eo_parameters["channel"], probe_eo_pulse)
        ttl_function = TTLPulses([[0, 4 * ureg.us]])
        probe.add_ttl_function(self._digitizer_channel, ttl_function)
        probe.add_ttl_function(self._field_plate_channel, TTLOn())
        self.add_segment(probe)

    def _add_break(self, break_time: Q_ = 10 * ureg.us):
        segment = SegmentEmpty("break", break_time)
        segment.add_ttl_function(self._field_plate_channel, TTLOn())
        self.add_segment(segment)
        segment = SegmentEmpty("delay", 1 * ureg.ms)
        segment.add_ttl_function(self._field_plate_channel, TTLOn())
        self.add_segment(segment)

    def setup_sequence(self):
        segment_repeats = []
        #segment_repeats.append(("carrier_burn", self._carrier_burn_repeats))
        #segment_repeats.append(("break", 1))

        segment_repeats.append((
            f"burn_{self._burn_parameters['transition']}",
            self._burn_repeats,
        ))
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
        segment_repeats.append(("delay", 100))

        for kk in range(self._pump_parameters["repeats"]):
            segment_repeats.append(("pump", 1))
            segment_repeats.append(("probe", 1))
        return super().setup_sequence(segment_repeats)
