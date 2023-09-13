from functools import partial
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import numpy as np
from onix.headers.awg.M4i6622 import SPCSEQ_END, SPCSEQ_ENDLOOPALWAYS
from onix.units import Q_

sample_rate = 625e6


class Segment:
    def __init__(self, name: str, duration: Optional[Union[float, Q_]] = None):
        self.name = name
        self._awg_pulses: Dict[int, AWGFunction] = {}
        self._ttl_pulses: Dict[int, TTLFunction] = {}
        if isinstance(duration, Q_):
            duration = duration.to("s").magnitude
        self._duration = duration

    def add_awg_function(self, channel: int, function):
        self._awg_pulses[channel] = function

    def add_ttl_function(self, channel: int, function):
        self._ttl_pulses[channel] = function

    def fill_all_channels(self, awg_channel_num: int, ttl_channels: List[int]):
        for channel in range(awg_channel_num):
            if channel not in self._awg_pulses:
                self.add_awg_function(channel, AWGZero())

        for channel in ttl_channels:
            if channel not in self._ttl_pulses:
                self.add_ttl_function(channel, TTLOff())

    def awg_functions(self, channel_num: int):
        functions = []
        for channel in range(channel_num):
            try:
                functions.append(self._awg_pulses[channel].output)
            except KeyError:
                raise KeyError(f"AWG channel {channel} is not defined in the {self.name} segment.")
        if len(self._awg_pulses) > channel_num:
            raise Exception(f"More AWG channels are defined than used in the {self.name} segment.")
        return functions

    def ttl_function(self, channels: List[int]):
        if len(channels) > 1:
            raise NotImplementedError("Needs to figure out how multiple TTL channels work with `configSequenceReplay`.")
        return self._ttl_pulses[channels[0]].output

    @property
    def duration(self) -> float:
        if self._duration is None:
            max_min_duration = 0
            for channel in self._awg_pulses:
                max_min_duration = np.max(
                    [max_min_duration, self._awg_pulses[channel].min_duration]
                )
            for channel in self._ttl_pulses:
                max_min_duration = np.max(
                    [max_min_duration, self._ttl_pulses[channel].min_duration]
                )
            if max_min_duration > 0:
                return max_min_duration
            else:
                raise Exception(f"The duration of the {self.name} segment must be defined.")
        return self._duration


class AWGFunction:
    def output(self, sample_indices):
        raise NotImplementedError()

    @property
    def min_duration(self) -> float:
        return 0


class AWGZero(AWGFunction):
    def output(self, sample_indices):
        return np.zeros(len(sample_indices))


class AWGSinePulse(AWGFunction):
    def __init__(
        self,
        frequency: Union[float, Q_],
        amplitude: float,
        phase: float = 0,
        start_time: Optional[Union[float, Q_]] = None,
        end_time: Optional[Union[float, Q_]] = None,
    ):
        super().__init__()
        if isinstance(frequency, Q_):
            frequency = frequency.to("Hz").magnitude
        self._frequency = frequency
        self._amplitude = amplitude
        self._phase = phase
        if isinstance(start_time, Q_):
            start_time = start_time.to("s").magnitude
        self._start_time = start_time
        if isinstance(end_time, Q_):
            end_time = end_time.to("s").magnitude
        self._end_time = end_time

    def output(self, sample_indices):
        times = sample_indices / sample_rate
        sine = self._amplitude * np.sin(2 * np.pi * self._frequency * times + self._phase)
        if self._start_time is not None:
            mask_start = np.heaviside(times - self._start_time, 0)
        else:
            mask_start = 1
        if self._end_time is not None:
            mask_end = np.heaviside(self._end_time - times, 1)
        else:
            mask_end = 1
        return sine * mask_start * mask_end

    @property
    def min_duration(self) -> float:
        if self._end_time is not None:
            return self._end_time
        if self._start_time is not None:
            return self._start_time
        return 0


class AWGSineSweep(AWGFunction):
    def __init__(
        self,
        start_frequency: Union[float, Q_],
        stop_frequency: Union[float, Q_],
        amplitude: float,
        start_time: Union[float, Q_],
        end_time: Union[float, Q_],
        phase: float = 0,
    ):
        super().__init__()
        if isinstance(start_frequency, Q_):
            start_frequency = start_frequency.to("Hz").magnitude
        self._start_frequency = start_frequency
        if isinstance(stop_frequency, Q_):
            stop_frequency = stop_frequency.to("Hz").magnitude
        self._stop_frequency = stop_frequency
        self._amplitude = amplitude
        if isinstance(start_time, Q_):
            start_time = start_time.to("s").magnitude
        self._start_time = start_time
        if isinstance(end_time, Q_):
            end_time = end_time.to("s").magnitude
        self._end_time = end_time
        self._phase = phase

    def output(self, sample_indices):
        times = sample_indices / sample_rate
        duration = self._end_time - self._start_time
        frequency_scan = self._stop_frequency - self._start_frequency
        instant_frequencies = (times - self._start_time) / duration * frequency_scan / 2 + self._start_frequency
        sine_sweep = self._amplitude * np.sin(2 * np.pi * instant_frequencies * times + self._phase)
        mask_start = np.heaviside(times - self._start_time, 0)
        mask_end = np.heaviside(self._end_time - times, 1)
        return sine_sweep * mask_start * mask_end

    @property
    def min_duration(self) -> float:
        return self._end_time


class AWGSineTrain(AWGFunction):
    def __init__(
        self,
        on_time: Union[float, Q_],
        off_time: Union[float, Q_],
        frequencies: Union[float, List[float], Q_],
        amplitudes: Union[float, List[float]],
        phases: Union[float, List[float]] = 0,
        start_time: Union[float, Q_] = 0,
    ):
        super().__init__()
        if isinstance(on_time, Q_):
            on_time = on_time.to("s").magnitude
        self._on_time = on_time
        if isinstance(off_time, Q_):
            off_time = off_time.to("s").magnitude
        self._off_time = off_time
        try:
            frequencies = Q_.from_list(frequencies)
        except Exception as e:
            pass
        if isinstance(frequencies, Q_):
            frequencies = frequencies.to("Hz").magnitude
        self._frequencies = frequencies
        self._amplitudes = amplitudes
        self._phases = phases
        if isinstance(start_time, Q_):
            start_time = start_time.to("s").magnitude
        self._start_time = start_time
        self._unify_lists()

    def _unify_lists(self):
        """Makes sure that frequencies, amplitudes, and phases are lists of the same length."""
        length = None
        try:
            self._frequencies[0]
            is_list_freq = True
            length = len(self._frequencies)
        except TypeError:
            is_list_freq = False

        try:
            self._amplitudes[0]
            is_list_amp = True
            length = len(self._amplitudes)
        except TypeError:
            is_list_amp = False

        try:
            self._phases[0]
            is_list_phase = True
            length = len(self._phases)
        except TypeError:
            is_list_phase = False

        if length is None:
            raise ValueError("At least one of the frequencies, amplitudes, and phases must be a list")

        if not is_list_freq:
            self._frequencies = np.repeat(self._frequencies, length)
        if not is_list_amp:
            self._amplitudes = np.repeat(self._amplitudes, length)
        if not is_list_phase:
            self._phases = np.repeat(self._phases, length)

        if len(self._frequencies) != len(self._amplitudes) or len(self._frequencies) != len(self._phases):
            raise ValueError("Frequencies, amplitudes, and phases must be of the same length.")

    def output(self, sample_indices):
        def sine(frequency, amplitude, phase, times):
            return amplitude * np.sin(2 * np.pi * frequency * times + phase)

        def zero(times):
            return np.zeros(len(times))

        times = sample_indices / sample_rate
        funclist = []
        condlist = []
        start_time = self._start_time
        for kk in range(len(self._frequencies)):
            end_time = start_time + self._on_time
            funclist.append(partial(sine, self._frequencies[kk], self._amplitudes[kk], self._phases[kk]))
            condlist.append(np.logical_and(times > start_time, times <= end_time))
            start_time = end_time + self._off_time
        funclist.append(zero)
        return np.piecewise(times, condlist, funclist)

    @property
    def min_duration(self) -> float:
        return self._start_time + len(self._frequencies) * (self._on_time + self._off_time)


class TTLFunction:
    def output(self, sample_indices):
        raise NotImplementedError()

    @property
    def min_duration(self) -> float:
        return 0


class TTLOff(TTLFunction):
    def output(self, sample_indices):
        return np.zeros(len(sample_indices))


class TTLOn(TTLFunction):
    def output(self, sample_indices):
        return np.ones(len(sample_indices))


class TTLPulses(TTLFunction):
    def __init__(self, on_times: Union[List[List[float]], Q_]):
        super().__init__()
        if isinstance(on_times, Q_):  # type detection does not cover list of quantities
            on_times = on_times.to("s").magnitude
        self._on_times = on_times

    def output(self, sample_indices):
        def on(times):
            return np.ones(len(times))

        def off(times):
            return np.zeros(len(times))

        times = sample_indices / sample_rate
        funclist = []
        condlist = []
        for time_group in self._on_times:
            start_time = time_group[0]
            end_time = time_group[1]
            funclist.append(on)
            condlist.append(np.logical_and(times > start_time, times <= end_time))
        funclist.append(off)
        return np.piecewise(times, condlist, funclist)

    @property
    def min_duration(self) -> float:
        return np.max(self._on_times)


class SegmentEmpty(Segment):
    def __init__(self, name: str = "empty", duration: Union[float, Q_] = 10e-6):
        if isinstance(duration, Q_):
            duration = duration.to("s").magnitude
        super().__init__(name, duration)


class Sequence:
    def __init__(
        self,
        awg_channel_num: int,
        ttl_channels: List[int],
        fill_channels_with_zero: Optional[bool] = True
    ):
        self._awg_channel_num = awg_channel_num
        self._ttl_channels = ttl_channels
        self._fill_channels_with_zero = fill_channels_with_zero
        self._segments = {"__last_step": SegmentEmpty()}
        self._segment_repeats = []

    def add_segment(self, name: str, segment: Segment):
        if name in self._segments:
            raise ValueError(f"Segment {name} already exists in the sequence.")
        self._segments[name] = segment

    def setup_sequence(self, segment_repeats: List[Tuple[str, int]]):
        self._segment_repeats = []
        for name, repeat in segment_repeats:
            if name in self._segments:
                self._segment_repeats.append((name, repeat))
            else:
                self._segment_repeats = []
                raise ValueError(f"Segment {name} is not defined.")
        if len(self._segment_repeats) > 0:
            self._segment_repeats.append(("__last_step", 1))
        else:
            raise Exception(f"Must implement at least one segment.")

    @property
    def segment_loops(self) -> List[int]:
        return [repeat for (name, repeat) in self._segment_repeats]

    @property
    def segment_steps(self) -> List[int]:
        segment_keys = list(self._segments)
        return [segment_keys.index(name) for name, repeat in self._segment_repeats]

    @property
    def segment_next(self) -> List[int]:
        num_of_steps = len(self.segment_steps)
        return list(np.linspace(1, num_of_steps - 1, num_of_steps - 1).astype(int)) + [0]

    @property
    def segment_durations(self) -> List[float]:
        return [self._segments[name].duration for name in self._segments]

    @property
    def segment_conditions(self) -> List[int]:
        conditions = []
        for kk in range(len(self._segment_repeats) - 1):
            conditions.append(SPCSEQ_ENDLOOPALWAYS)
        conditions.append(SPCSEQ_END)
        return conditions

    @property
    def segment_awg_functions(self) -> List[List[Callable[..., Any]]]:
        value = []
        for segment in self._segments.values():
            if self._fill_channels_with_zero or segment.name == "empty":
                segment.fill_all_channels(self._awg_channel_num, self._ttl_channels)
            value.append(segment.awg_functions(self._awg_channel_num))
        return value

    @property
    def segment_ttl_functions(self) -> List[Callable[..., Any]]:
        value = []
        for segment in self._segments.values():
            if self._fill_channels_with_zero or segment.name == "empty":
                segment.fill_all_channels(self._awg_channel_num, self._ttl_channels)
            value.append(segment.ttl_function(self._ttl_channels))
        return value

    @property
    def ttl_out_on(self) -> bool:
        return len(self._ttl_channels) > 0

    @property
    def total_duration(self) -> float:
        value = 0.0
        for name, repeat in self._segment_repeats:
            duration = self._segments[name].duration
            value += duration * repeat
        return value
