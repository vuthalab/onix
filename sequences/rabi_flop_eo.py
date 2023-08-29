from typing import List, Dict, Tuple, Optional, Union

from sequences.sequence import (
    Sequence,
    SegmentEmpty,
)
from sequences.shared import (
    SegmentBurn, SegmentProbe, SegmentPump, SegmentPumpSweep
)
from sequences.aom_settings import aoms
from units import Q_


class RabiFlop(Sequence):
    def __init__(
        self,
        probe_channel: str,
    ):
        self._probe_channel = probe_channel
        self._all_channels = ["ac", "cb", "bb"]
        if probe_channel not in self._all_channels:
            raise ValueError(f"Probe channel {probe_channel} is not defined.")
        self._pump_channels = self._all_channels.copy()
        self._pump_channels.remove(probe_channel)

    def add_burns(self, burn_width: Union[float, Q_], burn_time: Union[float, Q_]):
        for name in self._all_channels:
            f_start = aoms[name].center_frequency - burn_width / 2
            f_stop = aoms[name].center_frequency + burn_width / 2
            amplitude = aoms[name].max_amplitude
            channel = aoms[name].awg_channel
            segment = SegmentBurn(
                f"{name}_burn",
                burn_time,
                {
                    channel: {
                        "f_start": f_start,
                        "f_stop": f_stop,
                        "amplitude": amplitude,
                    },
                },
            )
            self.add_segment(segment.name, segment)

    def add_pumps(self, pump_time: Union[float, Q_]):
        for name in self._pump_channels:
            frequency = aoms[name].center_frequency
            amplitude = aoms[name].max_amplitude
            channel = aoms[name].awg_channel
            segment = SegmentPump(
                f"{name}_pump",
                pump_time,
                {
                    channel: {
                        "frequency": frequency,
                        "amplitude": amplitude,
                    },
                },
            )
            self.add_segment(segment.name, segment)

    def add_probe(
        self,
        probe_frequencies: Union[List[float], Q_],
        probe_amplitudes: Union[float, List[float]],
        on_time: Union[float, Q_],
        off_time: Union[float, Q_],
        ttl_start_time: Optional[Union[float, Q_]] = 12e-6,
        ttl_duration: Optional[Union[float, Q_]] = 4e-6,
        sequence_ttl_offset_time: Optional[Union[float, Q_]] = 4e-6,
    ) -> float:
        channel = aoms[self._probe_channel].awg_channel
        digitizer_channel = 0
        segment = SegmentProbe(
            f"{self._probe_channel}_probe",
            channel,
            digitizer_channel,
            probe_frequencies,
            probe_amplitudes,
            on_time,
            off_time,
            ttl_start_time,
            ttl_duration,
            sequence_ttl_offset_time,
        )
        self.add_segment(segment.name, segment)
        if isinstance(ttl_start_time, Q_):
            ttl_start_time = ttl_start_time.to("s").magnitude
        return segment.duration - ttl_start_time

    def add_break(self, break_time: Optional[Union[float, Q_]] = 10e-6):
        segment = SegmentEmpty("empty", break_time)
        self.add_segment("break", segment)

    def add_flop(
        self,
        flop_amplitudes: Union[float, List[float], Q_],
        flop_times: Union[float, List[float], Q_],
    ):


    def setup_sequence(self, probe_repeats: int = 1):
        segment_repeats = []
        segment_repeats.append((f"{self._probe_channel}_probe", probe_repeats))
        segment_repeats.append(("break", 1))
        for name in self._all_channels:
            segment_repeats.append((f"{name}_burn", 1))
            segment_repeats.append(("break", 1))
        segment_repeats.append((f"{self._probe_channel}_probe", probe_repeats))
        segment_repeats.append(("break", 1))
        for name in self._pump_channels:
            segment_repeats.append((f"{name}_pump", 1))
            segment_repeats.append(("break", 1))
        segment_repeats.append((f"{self._probe_channel}_probe", probe_repeats))
        segment_repeats.append(("break", 1))
        return super().setup_sequence(segment_repeats)
