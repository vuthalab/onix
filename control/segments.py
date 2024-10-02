import numbers

import numpy as np

from typing import Literal, Optional, Union

from onix.control.awg_functions import AWGFunction, AWGMultiFunctions, AWGZero
from onix.control.awg_maps import awg_channels
from onix.control.hardware import (AWG_MIN_SEGMENT_SAMPLE, AWG_SAMPLE_RATE,
                                   AWG_SEGMENT_SIZE_MULTIPLE)
from onix.control.ttl_functions import TTLFunction, TTLMultiFunctions, TTLOff
from onix.units import Q_, ureg


class Segment:
    def __init__(self, name: str, duration: Optional[Union[float, Q_]] = None):
        self.name = name
        self._awg_pulses: dict[int, AWGFunction] = {}
        self._ttl_pulses: dict[int, TTLFunction] = {}
        if isinstance(duration, numbers.Number):
            duration = duration * ureg.s
        self._duration: Union[Q_, None] = duration
        self._sample_rate = AWG_SAMPLE_RATE

        self._field_on = False

    def add_awg_function(self, channel: int, function: AWGFunction):
        if not isinstance(channel, int):
            raise ValueError(f"Channel {channel} must be an integer.")
        if function.max_amplitude > awg_channels[channel]["max_allowed_amplitude"]:
            raise ValueError(f"Channel {channel} exceeded maximum allowable amplitude.")
        self._awg_pulses[channel] = function

    def add_ttl_function(self, channel: int, function: TTLFunction):
        if not isinstance(channel, int):
            raise ValueError(f"Channel {channel} must be an integer.")
        self._ttl_pulses[channel] = function

    def _awg_pulses_of_channels(self, awg_channels: list[int]) -> list[AWGFunction]:
        pulses = []
        for channel in awg_channels:
            try:
                pulses.append(self._awg_pulses[channel])
            except KeyError:
                pulses.append(AWGZero())
        return pulses

    def _ttl_pulses_of_channels(self, ttl_channels: list[int]) -> list[TTLFunction]:
        pulses = []
        for channel in ttl_channels:
            try:
                pulses.append(self._ttl_pulses[channel])
            except KeyError:
                pulses.append(TTLOff())
        return pulses

    def get_sample_data(
        self,
        awg_channels: list[int],
        ttl_channels_map_to_awg_channels: dict[int, int],
        sample_indices: np.ndarray,
        sample_rate: float,
    ):
        """Returns data that is compatible with the M4i6622 AWG."""
        all_awg_indices = list(ttl_channels_map_to_awg_channels.values())
        if len(set(all_awg_indices)) < len(all_awg_indices):
            raise ValueError("Only supports TTL using the 16th bit.")
        ttl_channels = list(ttl_channels_map_to_awg_channels.keys())
        awg_pulses = self._awg_pulses_of_channels(awg_channels)
        ttl_pulses = self._ttl_pulses_of_channels(ttl_channels)

        times = sample_indices / sample_rate
        awg_data = [
            awg_pulse.output(times).astype(np.int16) for awg_pulse in awg_pulses
        ]  # TODO: slow
        ttl_data = [
            ttl_pulse.output(times).astype(np.int16) for ttl_pulse in ttl_pulses
        ]
        for kk, ttl_channel in enumerate(ttl_channels_map_to_awg_channels):
            awg_index = awg_channels.index(
                ttl_channels_map_to_awg_channels[ttl_channel]
            )
            awg_data[awg_index] = np.bitwise_or(
                np.right_shift(
                    awg_data[awg_index].view(np.uint16), 1
                ),  # right_shift only works properly on non-negative numbers.
                np.left_shift(ttl_data[kk], 15),
            )
        return np.array(awg_data).flatten("F")  # TODO: slow

    def set_electric_field(self, field_on: bool):
        self._field_on = field_on

    @property
    def field_on(self) -> bool:
        return self._field_on

    @property
    def awg_channels_used(self) -> list[int]:
        return list(self._awg_pulses)

    @property
    def ttl_channels_used(self) -> list[int]:
        return list(self._ttl_pulses)

    @property
    def duration(self) -> Q_:
        if self._duration is None:
            max_min_duration = 0 * ureg.s
            for channel in self._awg_pulses:
                if self._awg_pulses[channel].min_duration > max_min_duration:
                    max_min_duration = self._awg_pulses[channel].min_duration
            for channel in self._ttl_pulses:
                if self._ttl_pulses[channel].min_duration > max_min_duration:
                    max_min_duration = self._ttl_pulses[channel].min_duration
            if max_min_duration > 0 * ureg.s:
                return max_min_duration
            else:
                raise Exception(
                    f"The duration of the {self.name} segment must be defined."
                )
        return self._duration

    @property
    def actual_duration(self) -> Q_:
        sample_num = int(self.duration.to("s").magnitude * self._sample_rate)
        sample_num = (sample_num + AWG_SEGMENT_SIZE_MULTIPLE - 1) // AWG_SEGMENT_SIZE_MULTIPLE * AWG_SEGMENT_SIZE_MULTIPLE
        if sample_num < AWG_MIN_SEGMENT_SAMPLE:
            sample_num = AWG_MIN_SEGMENT_SAMPLE
        return sample_num / self._sample_rate * ureg.s


class MultiSegments(Segment):
    def __init__(self, name: str, segments: list[Segment]):
        super().__init__(name, duration=None)
        self._combine_segments(segments)

    def _combine_segments(self, segments: list[Segment]):
        awg_channels = set()
        ttl_channels = set()
        start_times = []
        end_times = []
        time_now = 0
        for segment in segments:
            start_times.append(time_now)
            time_now += segment.duration.to("s").magnitude
            end_times.append(time_now)
            for awg_channel in segment._awg_pulses:
                awg_channels.add(awg_channel)
            for ttl_channel in segment._ttl_pulses:
                ttl_channels.add(ttl_channel)
        start_times = np.array(start_times) * ureg.s
        end_times = np.array(end_times) * ureg.s

        for awg_channel in awg_channels:
            awg_pulse = AWGMultiFunctions(
                [segment._awg_pulses_of_channels([awg_channel])[0] for segment in segments],
                start_times,
                end_times,
            )
            self.add_awg_function(awg_channel, awg_pulse)
        for ttl_channel in ttl_channels:
            ttl_pulse = TTLMultiFunctions(
                [segment._ttl_pulses_of_channels([ttl_channel])[0] for segment in segments],
                start_times,
                end_times,
            )
            self.add_ttl_function(ttl_channel, ttl_pulse)


class SegmentEmpty(Segment):
    def __init__(self, name: str, duration: Union[float, Q_]):
        if isinstance(duration, numbers.Number):
            duration = duration * ureg.s
        super().__init__(name, duration)


class SegmentStart(SegmentEmpty):
    def __init__(self):
        super().__init__("__start", 1 * ureg.us)


class SegmentEnd(SegmentEmpty):
    def __init__(self):
        super().__init__("__end", 1 * ureg.us)


class SingleBoardSegments:
    """Stores all segments that should be replayed on one AWG board."""
    def __init__(self, available_ttl_channels: list[int], available_awg_channels: list[int]):
        self._available_ttl_channels = available_ttl_channels
        self._available_awg_channels = available_awg_channels
        self._segments: dict[str, Segment] = {}
        self._segment_steps: list[tuple[str, int]] = []
        self.add_segment(SegmentStart())
        self.add_segment(SegmentEnd())
        self._loop = (None, [None])

    def add_segment(self, segment: Segment, ignore_repeat_name: bool = True):
        name = segment.name
        if name in self._segments:
            if ignore_repeat_name:
                return
            raise ValueError(f"Segment {name} already exists in the sequence.")
        
        # check if the segment contains channels for this board.
        # if not, replace the segment with a empty segment
        # the empty segment will be replaced with standard filler segments before programming.
        segment_contains_awg_channel_of_this_board = False
        for kk in segment.awg_channels_used:
            if kk in self._available_awg_channels:
                segment_contains_awg_channel_of_this_board = True
        segment_contains_ttl_channel_of_this_board = False
        for kk in segment.ttl_channels_used:
            if kk in self._available_ttl_channels:
                segment_contains_ttl_channel_of_this_board = True
        if name.startswith("__") or segment_contains_awg_channel_of_this_board or segment_contains_ttl_channel_of_this_board:
            self._segments[name] = segment
        else:
            name = f"__empty_{name}"
            self._segments[name] = SegmentEmpty(name, segment.duration)

    def insert_segments(self, segments: dict[str, Segment]):
        """This function should only be called by the awg device directly."""
        segments = segments.copy()
        for name in segments:
            if name in self._segments:
                self._segments.pop(name)
        segments.update(self._segments)
        self._segments = segments

    def _get_filler_steps(self, empty_duration: Q_):
        """Decompose the duration with no pulse to standard building elements of filler segments."""
        if empty_duration <= 0 * ureg.s:
            return []
        filler_segment_steps = []
        # standard filler length is 1 ms.
        # this is not too long to occupy too much AWG memory
        # and it is not too short to require too many loops for a reasonable sequence shorter than ~1000 seconds.
        filler_1ms_name = "__filler_1ms"
        if filler_1ms_name not in self._segments:
            filler_1ms = SegmentEmpty(filler_1ms_name, 1 * ureg.ms)
            self.add_segment(filler_1ms)
        else:
            filler_1ms = self._segments[filler_1ms_name]
        filler_1ms_duration = filler_1ms.actual_duration
        # minus one makes sure that the additional filler step is not too short.
        num_filler_1ms = int(empty_duration / filler_1ms_duration) - 1
        if num_filler_1ms > 0:
            filler_segment_steps.append((filler_1ms_name, num_filler_1ms))
        else:
            num_filler_1ms = 0
        addi_filler_duration = empty_duration - num_filler_1ms * filler_1ms_duration
        if addi_filler_duration > 0 * ureg.s:
            addi_filler_duration_name = f"__filler_{addi_filler_duration}"
            filler_addi = SegmentEmpty(addi_filler_duration_name, addi_filler_duration)
            self.add_segment(filler_addi)
            filler_segment_steps.append((addi_filler_duration_name, 1))

        return filler_segment_steps        

    def _combine_empty_steps(self):
        new_segment_steps = []
        empty_duration = 0 * ureg.s
        for kk, (name, repeat) in enumerate(self._segment_steps):
            if name.startswith("__empty"):
                empty_duration += self._segments[name].actual_duration * repeat
            else:
                new_segment_steps.extend(self._get_filler_steps(empty_duration))
                empty_duration = 0 * ureg.s
                new_segment_steps.append((name, repeat))
        self._segment_steps = new_segment_steps

    def setup_loops(self, segments_to_replace: tuple[str], segments_to_loop_over: list[tuple[str]]):
        """Setup looping over segments.
        
        If looping over segments is needed, call this before calling `self.setup_sequence`.
        """
        all_names = list(segments_to_replace)
        for kk in segments_to_loop_over:
            all_names += list(kk)
        for name in all_names:
            if name not in self._segments and f"__empty_{name}" not in self._segments:
                raise ValueError(f"Segment {name} is not defined.")
        self._loop = (segments_to_replace, segments_to_loop_over)

    def setup_sequence(self, segment_steps: list[tuple[str, int]]):
        self._segment_steps = []
        segments_to_replace, segments_to_loop_over = self._loop
        for segments_to_use in segments_to_loop_over:
            self._segment_steps.append(("__start", 1))
            for name, repeat in segment_steps:
                if repeat == 0:
                    continue
                if segments_to_replace is not None and name in segments_to_replace:
                    name = segments_to_use[segments_to_replace.index(name)]
                empty_name = f"__empty_{name}"
                if name in list(self._segments):
                    if self._segments[name].duration > 0 * ureg.s:
                        self._segment_steps.append((name, repeat))
                elif empty_name in self._segments:
                    if self._segments[empty_name].duration > 0 * ureg.s:
                        self._segment_steps.append((empty_name, repeat))
                else:
                    self._segment_steps = []
                    raise ValueError(f"Segment {name} is not defined.")
            self._segment_steps.append(("__end", 1))
        self._combine_empty_steps()

    @property
    def segments(self) -> list[Segment]:
        return list(set([self._segments[name] for name, steps in self._segment_steps]))

    @property
    def steps(
        self,
    ) -> list[
        tuple[
            int, int, int, int, Literal["end_loop", "end_loop_on_trig", "end_sequence"]
        ]
    ]:
        segment_steps = []
        for step_number, (name, loops) in enumerate(self._segment_steps):
            segment_number = [seg.name for seg in self.segments].index(name)
            next_step = step_number + 1
            if step_number == len(self._segment_steps) - 1:
                end = "end_sequence"
            elif name == "__end" and self._loop[0] is not None:
                end = "end_loop_on_trig"
            else:
                end = "end_loop"
            segment_steps.append((step_number, segment_number, next_step, loops, end))
        return segment_steps

    @property
    def total_duration(self) -> Q_:
        value = 0 * ureg.s
        for name, repeat in self._segment_steps:
            duration = self._segments[name].actual_duration
            value += duration * repeat
        return value


class AllBoardSegments:
    def __init__(self, awg_board_count: int = 2):
        self.single_board_segments: dict[int, SingleBoardSegments] = {}
        for kk in range(awg_board_count):
            ttl_channels = list(range(kk * 3, (kk + 1) * 3))
            awg_channels = list(range(kk * 4, (kk + 1) * 4))
            self.single_board_segments[kk] = SingleBoardSegments(
                ttl_channels, awg_channels
            )

    def add_segment(self, segment: Segment, ignore_repeat_name: bool = True):
        for kk in self.single_board_segments:
            self.single_board_segments[kk].add_segment(segment, ignore_repeat_name)

    def insert_segments(self, segments: dict[str, Segment]):
        """This function should only be called by the awg device directly."""
        for kk in self.single_board_segments:
            self.single_board_segments[kk].insert_segments(segments)

    def setup_loops(self, segments_to_replace: tuple[str], segments_to_loop_over: list[tuple[str]]):
        """Setup looping over segments.
        
        If looping over segments is needed, call this before calling `self.setup_sequence`.
        """
        for kk in self.single_board_segments:
            if kk != 0:
                self.single_board_segments[kk].setup_loops(
                    segments_to_replace, segments_to_loop_over
                )

    def setup_sequence(self, segment_steps: list[tuple[str, int]]):
        for kk in self.single_board_segments:
            self.single_board_segments[kk].setup_sequence(segment_steps)

    def segments(self, board_index: int) -> list[Segment]:
        return self.single_board_segments[board_index].segments
    
    def steps(self, board_index: int) -> list[
        tuple[
            int, int, int, int, Literal["end_loop", "end_loop_on_trig", "end_sequence"]
        ]
    ]:
        return self.single_board_segments[board_index].steps
