from typing import List, Dict, Tuple, Optional, Union

from onix.sequences.sequence import (
    Sequence,
    Segment,
    SegmentEmpty,
    AWGSinePulse,
    AWGSineSweep,
    AWGSineTrain,
    TTLPulses,
)
from onix.models.hyperfine import energies
from onix.units import Q_, ureg
from onix.headers.awg.M4i6622 import M4i6622
from onix.headers.digitizer import DigitizerVisa


class AntiholeLifetime(Sequence):
    def __init__(
        self,
        probe_transition: str,
        eo_channel: int,
        eo_offset_frequency: Q_,
        switch_aom_channel: int,
        switch_aom_frequency: Q_,
        switch_aom_amplitude: int,
        detect_aom_channel: int,
        detect_aom_frequency: Q_,
        detect_aom_amplitude: int,
        repeats: int,
    ):
        super().__init__()
        self._probe_transition = probe_transition
        self._burn_transitions = ["bb"]
        self._pump_transitions = ["ab", "cb"]
        self._eo_channel = eo_channel
        self._eo_offset_frequency = eo_offset_frequency
        self._switch_aom_channel = switch_aom_channel
        self._switch_aom_frequency = switch_aom_frequency
        self._switch_aom_amplitude = switch_aom_amplitude
        self._detect_aom_channel = detect_aom_channel
        self._detect_aom_frequency = detect_aom_frequency
        self._detect_aom_amplitude = detect_aom_amplitude
        self._build_aom_pulse()
        self._repeats = repeats

    def _build_aom_pulse(self):
        self._switch_aom_pulse = AWGSinePulse(
            self._switch_aom_frequency, self._switch_aom_amplitude
        )
        self._detect_aom_pulse = AWGSinePulse(
            self._detect_aom_frequency, self._detect_aom_amplitude
        )

    def add_burns(self, burn_width: Q_, burn_time: Q_, burn_amplitude: int):
        burn_piecewise_time = 10 * ureg.ms
        self._burn_counts = 1
        if burn_time > burn_piecewise_time:
            self._burn_counts = int(burn_time / burn_piecewise_time)
            burn_time = burn_piecewise_time
        for name in self._burn_transitions:
            F_state = name[0]
            D_state = name[1]
            frequency = energies["5D0"][D_state] - energies["7F0"][F_state] + self._eo_offset_frequency
            lower_limit = frequency - burn_width / 2
            upper_limit = frequency + burn_width / 2
            print(name, "burn", lower_limit, upper_limit)
            segment = Segment(f"burn_{name}", burn_piecewise_time)
            segment.add_awg_function(self._switch_aom_channel, self._switch_aom_pulse)
            segment.add_awg_function(self._eo_channel, AWGSineSweep(lower_limit, upper_limit, burn_amplitude, 0, burn_piecewise_time))
            self.add_segment(segment)

    def add_pumps(self, pump_time: Q_, pump_amplitude: int):
        pump_piecewise_time = 10 * ureg.ms
        self._pump_counts = 1
        if pump_time > pump_piecewise_time:
            self._pump_counts = int(pump_time / pump_piecewise_time)
            pump_time = pump_piecewise_time
        for name in self._pump_transitions:
            F_state = name[0]
            D_state = name[1]
            frequency = energies["5D0"][D_state] - energies["7F0"][F_state] + self._eo_offset_frequency
            segment = Segment(f"pump_{name}", pump_piecewise_time)
            segment.add_awg_function(self._switch_aom_channel, self._switch_aom_pulse)
            segment.add_awg_function(self._eo_channel, AWGSinePulse(frequency, pump_amplitude))
            self.add_segment(segment)

    def add_probe(
        self,
        probe_detunings: Q_,
        probe_amplitude: float,
        aom_probe_amplitude: float,
        on_time: Q_,
        off_time: Q_,
        ttl_probe_offset_time: Q_ = 4 * ureg.us,
        ttl_start_time: Q_ = 12 * ureg.us,
        ttl_duration: Q_ = 4 * ureg.us,
    ):
        F_state = self._probe_transition[0]
        D_state = self._probe_transition[1]
        probe_frequencies = energies["5D0"][D_state] - energies["7F0"][F_state] + self._eo_offset_frequency + probe_detunings
        digitizer_channel = 0

        segment = Segment("probe")
        ttl_stop_time = ttl_start_time + ttl_duration
        ttl_function = TTLPulses([[ttl_start_time, ttl_stop_time]])
        segment.add_ttl_function(digitizer_channel, ttl_function)
        start_time = ttl_start_time + ttl_probe_offset_time

        eo_function = AWGSineTrain(
            on_time, off_time, probe_frequencies, probe_amplitude, start_time=start_time
        )
        print("probe", probe_frequencies)
        segment.add_awg_function(self._eo_channel, eo_function)

        ao_function = AWGSineTrain(
            on_time, off_time, self._switch_aom_frequency, [aom_probe_amplitude] * len(probe_frequencies), start_time=start_time
        )
        segment.add_awg_function(self._switch_aom_channel, ao_function)
        segment.add_awg_function(self._detect_aom_channel, self._detect_aom_pulse)
        segment._duration = segment.duration + ttl_probe_offset_time
        self.add_segment(segment)

        self.probe_read_time = segment.duration - ttl_start_time

    def add_break(self, long_break_time, break_time: Q_ = 10 * ureg.us):
        segment = SegmentEmpty("break", break_time)
        self.add_segment(segment)
        long_break_piecewise_time = 10 * ureg.ms
        self._long_break_counts = 1
        if long_break_time > long_break_piecewise_time:
            self._long_break_counts = int(long_break_time / long_break_piecewise_time)
            long_break_time = long_break_piecewise_time
        segment = SegmentEmpty("long_break", long_break_piecewise_time)
        self.add_segment(segment)

    def setup_sequence(self, probe_repeats: int = 1):
        self._probe_repeats = probe_repeats
        segment_repeats = []
        for kk in range(probe_repeats):
            segment_repeats.append(("probe", 1))
            segment_repeats.append(("break", 1))

        for name in self._burn_transitions:
            segment_repeats.append((f"burn_{name}", self._burn_counts))
        for kk in range(probe_repeats):
            segment_repeats.append(("probe", 1))
            segment_repeats.append(("break", 1))

        for kk in range(self._pump_counts):
            for name in self._pump_transitions:
                segment_repeats.append((f"pump_{name}", 1))
        for kk in range(probe_repeats):
            segment_repeats.append(("probe", 1))
            segment_repeats.append(("long_break", self._long_break_counts))
        return super().setup_sequence(segment_repeats)

    def num_of_records(self) -> int:
        # the AWG always triggers the digitizer once when it runs.
        # First sample should be discarded.
        return 3 * self._probe_repeats + 1
