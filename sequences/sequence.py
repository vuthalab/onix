from functools import partial
from typing import Dict, List, Literal, Optional, Tuple, Union
import numbers

import numpy as np
from onix.units import Q_, ureg


class Segment:
    def __init__(self, name: str, duration: Optional[Union[float, Q_]] = None):
        self.name = name
        self._awg_pulses: Dict[int, AWGFunction] = {}
        self._ttl_pulses: Dict[int, TTLFunction] = {}
        if isinstance(duration, numbers.Number):
            duration = duration * ureg.s
        self._duration: Union[Q_, None] = duration

    def add_awg_function(self, channel: int, function):
        if not isinstance(channel, int):
            raise ValueError(f"Channel {channel} must be an integer.")
        self._awg_pulses[channel] = function

    def add_ttl_function(self, channel: int, function):
        if not isinstance(channel, int):
            raise ValueError(f"Channel {channel} must be an integer.")
        self._ttl_pulses[channel] = function

    def _fill_all_channels(self, awg_channels: List[int], ttl_channels: List[int]):
        for channel in awg_channels:
            if channel not in self._awg_pulses:
                self.add_awg_function(channel, AWGZero())

        for channel in ttl_channels:
            if channel not in self._ttl_pulses:
                self.add_ttl_function(channel, TTLOff())

    def _awg_functions(self, awg_channels: List[int]):
        functions = []
        for channel in awg_channels:
            try:
                functions.append(self._awg_pulses[channel].output)
            except KeyError:
                raise KeyError(
                    f"AWG channel {channel} is not defined in the {self.name} segment."
                )
        if len(self._awg_pulses) > len(awg_channels):
            raise Exception(
                f"More AWG channels are defined than used in the {self.name} segment."
            )
        return functions

    def _ttl_functions(self, ttl_channels: List[int]):
        functions = []
        for channel in ttl_channels:
            try:
                functions.append(self._ttl_pulses[channel].output)
            except KeyError:
                raise KeyError(
                    f"TTL channel {channel} is not defined in the {self.name} segment."
                )
        if len(self._ttl_pulses) > len(ttl_channels):
            raise Exception(
                f"More TTL channels are defined than used in the {self.name} segment."
            )
        return functions

    def get_sample_data(
        self,
        awg_channels: List[int],
        ttl_channels_map_to_awg_channels: Dict[int, int],
        sample_indices: np.ndarray,
        sample_rate: float,
    ):
        """Returns data that is compatible with the M4i6622 AWG."""
        ttl_channels = list(ttl_channels_map_to_awg_channels.keys())
        self._fill_all_channels(awg_channels, ttl_channels)
        awg_functions = self._awg_functions(awg_channels)
        ttl_functions = self._ttl_functions(ttl_channels)

        times = sample_indices / sample_rate
        awg_data = [awg_function(times).astype(np.int16) for awg_function in awg_functions]
        ttl_data = [ttl_function(times) for ttl_function in ttl_functions]
        for ttl_channel in ttl_channels_map_to_awg_channels:
            awg_index = awg_channels.index(
                ttl_channels_map_to_awg_channels[ttl_channel]
            )
            awg_data[awg_index] = np.right_shift(awg_data[awg_index], 1)
        for kk, ttl_channel in enumerate(ttl_channels_map_to_awg_channels):
            awg_index = awg_channels.index(
                ttl_channels_map_to_awg_channels[ttl_channel]
            )
            awg_data[awg_index] = np.left_shift(awg_data[awg_index], 1)
            awg_data[awg_index] = np.bitwise_or(awg_data[awg_index], ttl_data[kk])
        return np.array(awg_data).flatten("F")

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


class AWGFunction:
    def output(self, times):
        raise NotImplementedError()

    @property
    def min_duration(self) -> Q_:
        return 0 * ureg.s


class AWGZero(AWGFunction):
    def output(self, times):
        return np.zeros(len(times))


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
        if isinstance(frequency, numbers.Number):
            frequency = frequency * ureg.Hz
        self._frequency: Q_ = frequency
        self._amplitude = amplitude
        self._phase = phase
        if isinstance(start_time, numbers.Number):
            start_time = start_time * ureg.s
        self._start_time: Union[Q_, None] = start_time
        if isinstance(end_time, numbers.Number):
            end_time = end_time * ureg.s
        self._end_time: Union[Q_, None] = end_time

    def output(self, times):
        frequency = self._frequency.to("Hz").magnitude
        sine = self._amplitude * np.sin(2 * np.pi * frequency * times + self._phase)
        if self._start_time is not None:
            start_time = self._start_time.to("s").magnitude
            mask_start = np.heaviside(times - start_time, 0)
        else:
            mask_start = 1
        if self._end_time is not None:
            end_time = self._end_time.to("s").magnitude
            mask_end = np.heaviside(end_time - times, 1)
        else:
            mask_end = 1
        return sine * mask_start * mask_end

    @property
    def min_duration(self) -> Q_:
        if self._end_time is not None:
            return self._end_time
        if self._start_time is not None:
            return self._start_time
        return 0 * ureg.s


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
        if isinstance(start_frequency, numbers.Number):
            start_frequency = start_frequency * ureg.Hz
        self._start_frequency: Q_ = start_frequency
        if isinstance(stop_frequency, numbers.Number):
            stop_frequency = stop_frequency * ureg.Hz
        self._stop_frequency: Q_ = stop_frequency
        self._amplitude = amplitude
        if isinstance(start_time, numbers.Number):
            start_time = start_time * ureg.s
        self._start_time: Q_ = start_time
        if isinstance(end_time, numbers.Number):
            end_time = end_time * ureg.s
        self._end_time: Q_ = end_time
        self._phase = phase

    def output(self, times):
        """Scanning half of the frequency is actually scanning the full range."""
        start_frequency = self._start_frequency.to("Hz").magnitude
        stop_frequency = self._stop_frequency.to("Hz").magnitude
        start_time = self._start_time.to("s").magnitude
        end_time = self._end_time.to("s").magnitude
        duration = end_time - start_time
        frequency_scan = stop_frequency - start_frequency
        instant_frequencies = (
            times - start_time
        ) / duration * frequency_scan / 2 + start_frequency
        sine_sweep = self._amplitude * np.sin(
            2 * np.pi * instant_frequencies * times + self._phase
        )
        mask_start = np.heaviside(times - start_time, 0)
        mask_end = np.heaviside(end_time - times, 1)
        return sine_sweep * mask_start * mask_end

    @property
    def min_duration(self) -> Q_:
        return self._end_time


class AWGSineTrain(AWGFunction):
    def __init__(
        self,
        on_time: Union[float, Q_],
        off_time: Union[float, Q_],
        frequencies: Union[float, List[float], Q_, List[Q_]],
        amplitudes: Union[float, List[float]],
        phases: Union[float, List[float]] = 0,
        start_time: Union[float, Q_] = 0,
    ):
        super().__init__()
        if isinstance(on_time, numbers.Number):
            on_time = on_time * ureg.s
        self._on_time: Q_ = on_time
        if isinstance(off_time, numbers.Number):
            off_time = off_time * ureg.s
        self._off_time: Q_ = off_time
        if isinstance(frequencies, numbers.Number):
            frequencies = frequencies * ureg.Hz
        elif not isinstance(frequencies, Q_):
            new_frequencies = []
            for frequency in frequencies:
                if isinstance(frequency, numbers.Number):
                    frequency = frequency * ureg.Hz
            frequencies = Q_.from_list(new_frequencies)
        self._frequencies: Q_ = frequencies
        self._amplitudes = amplitudes
        self._phases = phases
        if isinstance(start_time, numbers.Number):
            start_time = start_time * ureg.s
        self._start_time: Q_ = start_time
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
            raise ValueError(
                "At least one of the frequencies, amplitudes, and phases must be a list"
            )

        if not is_list_freq:
            frequency_value = self._frequencies.to("Hz").magnitude
            self._frequencies = np.repeat(frequency_value, length) * ureg.Hz
        if not is_list_amp:
            self._amplitudes = np.repeat(self._amplitudes, length)
        if not is_list_phase:
            self._phases = np.repeat(self._phases, length)

        if len(self._frequencies) != len(self._amplitudes) or len(
            self._frequencies
        ) != len(self._phases):
            raise ValueError(
                "Frequencies, amplitudes, and phases must be of the same length."
            )

    def output(self, times):
        def sine(frequency, amplitude, phase, times):
            return amplitude * np.sin(2 * np.pi * frequency * times + phase)

        def zero(times):
            return np.zeros(len(times))

        funclist = []
        condlist = []
        start_time = self._start_time.to("s").magnitude
        on_time = self._on_time.to("s").magnitude
        off_time = self._off_time.to("s").magnitude
        frequencies = self._frequencies.to("Hz").magnitude
        for kk in range(len(frequencies)):
            end_time = start_time + on_time
            funclist.append(
                partial(sine, frequencies[kk], self._amplitudes[kk], self._phases[kk])
            )
            condlist.append(np.logical_and(times > start_time, times <= end_time))
            start_time = end_time + off_time
        funclist.append(zero)
        return np.piecewise(times, condlist, funclist)

    @property
    def min_duration(self) -> Q_:
        return self._start_time + len(self._frequencies) * (
            self._on_time + self._off_time
        )


class TTLFunction:
    def output(self, times):
        raise NotImplementedError()

    @property
    def min_duration(self) -> Q_:
        return 0 * ureg.s


class TTLOff(TTLFunction):
    def output(self, times):
        return np.zeros(len(times), dtype=int)


class TTLOn(TTLFunction):
    def output(self, times):
        return np.ones(len(times), dtype=int)


class TTLPulses(TTLFunction):
    def __init__(self, on_times: Union[List[Union[List[Union[float, Q_]], Q_]], Q_]):
        super().__init__()
        if not isinstance(on_times, Q_):
            new_on_times = []
            for time_group in on_times:
                start = time_group[0]
                end = time_group[1]
                if isinstance(start, Q_):
                    start = start.to("s").magnitude
                if isinstance(end, Q_):
                    end = end.to("s").magnitude
                new_on_times.append([start, end])
            on_times = new_on_times * ureg.s
        self._on_times: Q_ = on_times

    def output(self, times):
        def on(times):
            return np.ones(len(times), dtype=int)

        def off(times):
            return np.zeros(len(times), dtype=int)

        funclist = []
        condlist = []
        on_times = self._on_times.to("s").magnitude
        for time_group in on_times:
            start_time = time_group[0]
            end_time = time_group[1]
            funclist.append(on)
            condlist.append(np.logical_and(times > start_time, times <= end_time))
        funclist.append(off)
        return np.piecewise(times, condlist, funclist)

    @property
    def min_duration(self) -> Q_:
        return np.max(self._on_times)


class SegmentEmpty(Segment):
    def __init__(self, name: str, duration: Union[float, Q_]):
        if isinstance(duration, numbers.Number):
            duration = duration * ureg.s
        super().__init__(name, duration)


class Sequence:
    def __init__(self):
        self._segments: Dict[str, Segment] = {}
        self._segment_steps: List[Tuple[str, int]] = []

    def add_segment(self, segment: Segment):
        name = segment.name
        if name in self._segments:
            raise ValueError(f"Segment {name} already exists in the sequence.")
        self._segments[name] = segment

    def insert_segments(self, segments: Dict[str, Segment]):
        """This function should only be called by the awg device directly."""
        for name in segments:
            if name in self._segments:
                raise ValueError(f"Segment {name} already exists in the sequence.")
        self._segments = segments.update(self._segments)

    def setup_sequence(self, segment_steps: List[Tuple[str, int]]):
        self._segment_steps = []
        for name, repeat in segment_steps:
            if name in self._segments:
                self._segment_steps.append((name, repeat))
            else:
                self._segment_steps = []
                raise ValueError(f"Segment {name} is not defined.")

    @property
    def segments(self) -> List[Segment]:
        return list(self._segments.values())

    @property
    def steps(
        self,
    ) -> List[
        Tuple[
            int, int, int, int, Literal["end_loop", "end_loop_on_trig", "end_sequence"]
        ]
    ]:
        segment_steps = []
        for step_number, (name, loops) in enumerate(self._segment_steps):
            segment_number = list(self._segments.keys()).index(name)
            if step_number == len(self._segment_steps) - 1:
                next_step = 0
                end = "end_sequence"
            else:
                next_step += step_number + 1
                end = "end_loop"
            segment_steps.append((step_number, segment_number, next_step, loops, end))
        return segment_steps

    @property
    def total_duration(self) -> Q_:
        value = 0 * ureg.s
        for name, repeat in self._segment_steps:
            duration = self._segments[name].duration
            value += duration * repeat
        return value
