from functools import partial
from typing import Dict, List, Literal, Optional, Tuple, Union
import numbers

import numpy as np
from onix.units import Q_, ureg
from onix.awg_maps import awg_channels

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
        if function.max_amplitude > awg_channels[channel]["max_allowed_amplitude"]:
            raise ValueError(f"Channel {channel} exceeded maximum allowable amplitude.")
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
        return functions

    def get_sample_data(
        self,
        awg_channels: List[int],
        ttl_channels_map_to_awg_channels: Dict[int, int],
        sample_indices: np.ndarray,
        sample_rate: float,
    ):
        """Returns data that is compatible with the M4i6622 AWG."""
        all_awg_indices = list(ttl_channels_map_to_awg_channels.values())
        if len(set(all_awg_indices)) < len(all_awg_indices):
            raise ValueError("Only supports TTL using the 16th bit.")
        ttl_channels = list(ttl_channels_map_to_awg_channels.keys())
        self._fill_all_channels(awg_channels, ttl_channels)
        awg_functions = self._awg_functions(awg_channels)
        ttl_functions = self._ttl_functions(ttl_channels)

        times = sample_indices / sample_rate
        awg_data = [
            awg_function(times).astype(np.int16) for awg_function in awg_functions
        ]  # TODO: slow
        ttl_data = [
            ttl_function(times).astype(np.int16) for ttl_function in ttl_functions
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


class MultiSegments(Segment):
    def __init__(self, name: str, segments: List[Segment]):
        super().__init__(name, duration=None)
        self._combine_segments(segments)

    def _combine_segments(self, segments: List[Segment]):
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

        for segment in segments:
            segment._fill_all_channels(list(awg_channels), list(ttl_channels))
        for awg_channel in awg_channels:
            awg_pulse = AWGMultiFunctions(
                [segment._awg_pulses[awg_channel] for segment in segments],
                start_times,
                end_times,
            )
            self.add_awg_function(awg_channel, awg_pulse)
        for ttl_channel in ttl_channels:
            ttl_pulse = TTLMultiFunctions(
                [segment._ttl_pulses[ttl_channel] for segment in segments],
                start_times,
                end_times,
            )
            self.add_ttl_function(ttl_channel, ttl_pulse)


class AWGFunction:
    def output(self, times):
        raise NotImplementedError()

    @property
    def min_duration(self) -> Q_:
        return 0 * ureg.s

    @property
    def max_amplitude(self):
        raise NotImplementedError("Maximum amplitude must be defined.")

class AWGZero(AWGFunction):
    def output(self, times):
        return np.zeros(len(times))

    @property
    def max_amplitude(self):
        return 0

class AWGConstant(AWGFunction):
    def __init__(self, amplitude: float):
        super().__init__()
        self._amplitude = amplitude

    def output(self, times):
        return np.ones(len(times)) * self._amplitude

    @property
    def max_amplitude(self):
        return self._amplitude

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

    @property
    def max_amplitude(self):
        return self._amplitude

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

    @property
    def max_amplitude(self):
        return self._amplitude

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
            for kk in range(len(frequencies)):
                if isinstance(frequencies[kk], numbers.Number):
                    frequencies[kk] = frequencies[kk] * ureg.Hz
            frequencies = Q_.from_list(frequencies, "Hz")
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
        except Exception:
            is_list_freq = False

        try:
            self._amplitudes[0]
            is_list_amp = True
            length = len(self._amplitudes)
        except Exception:
            is_list_amp = False

        try:
            self._phases[0]
            is_list_phase = True
            length = len(self._phases)
        except Exception:
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

    @property
    def max_amplitude(self):
        return np.max(self._amplitudes)

class AWGMultiFunctions(AWGFunction):
    def __init__(self, functions: List[AWGFunction], start_times: Q_, end_times: Q_):
        super().__init__()
        self._functions = functions
        self._start_times = start_times
        self._end_times = end_times

    def output(self, times):
        def zero(times):
            return np.zeros(len(times))

        funclist = []
        condlist = []
        for kk in range(len(self._start_times)):
            start_time = self._start_times[kk].to("s").magnitude
            end_time = self._end_times[kk].to("s").magnitude
            def output(function, start_time, times):
                return function.output(times - start_time)
            funclist.append(partial(output, self._functions[kk], start_time))
            condlist.append(np.logical_and(times > start_time, times <= end_time))
        funclist.append(zero)
        return np.piecewise(times, condlist, funclist)

    @property
    def min_duration(self) -> Q_:
        return max(self._end_times)

    @property
    def max_amplitude(self):
        return np.max([function.max_amplitude for function in self._functions])

class TTLFunction:
    def output(self, times):
        raise NotImplementedError()

    @property
    def min_duration(self) -> Q_:
        return 0 * ureg.s


class TTLOff(TTLFunction):
    def output(self, times):
        return np.zeros(len(times), dtype=np.int16)


class TTLOn(TTLFunction):
    def output(self, times):
        return np.ones(len(times), dtype=np.int16)


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
            return np.ones(len(times), dtype=np.int16)

        def off(times):
            return np.zeros(len(times), dtype=np.int16)

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


class TTLMultiFunctions(TTLFunction):
    def __init__(self, functions: List[TTLFunction], start_times: Q_, end_times: Q_):
        super().__init__()
        self._functions = functions
        self._start_times = start_times
        self._end_times = end_times

    def output(self, times):
        def zero(times):
            return np.zeros(len(times))

        funclist = []
        condlist = []
        for kk in range(len(self._start_times)):
            start_time = self._start_times[kk].to("s").magnitude
            end_time = self._end_times[kk].to("s").magnitude
            def output(function, start_time, times):
                return function.output(times - start_time)
            funclist.append(partial(output, self._functions[kk], start_time))
            condlist.append(np.logical_and(times > start_time, times <= end_time))
        funclist.append(zero)
        return np.piecewise(times, condlist, funclist)

    @property
    def min_duration(self) -> Q_:
        return max(self._end_times)


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


class Sequence:
    def __init__(self):
        self._segments: Dict[str, Segment] = {}
        self._segment_steps: List[Tuple[str, int]] = []
        self.add_segment(SegmentStart())
        self.add_segment(SegmentEnd())

    def add_segment(self, segment: Segment):
        name = segment.name
        if name in self._segments:
            raise ValueError(f"Segment {name} already exists in the sequence.")
        self._segments[name] = segment

    def insert_segments(self, segments: Dict[str, Segment]):
        """This function should only be called by the awg device directly."""
        segments = segments.copy()
        for name in segments:
            if name in self._segments:
                self._segments.pop(name)
        segments.update(self._segments)
        self._segments = segments

    def setup_sequence(self, segment_steps: List[Tuple[str, int]]):
        self._segment_steps = []
        self._segment_steps.append(("__start", 1))
        for name, repeat in segment_steps:
            if repeat == 0:
                continue
            if name in self._segments:
                if self._segments[name].duration > 0 * ureg.s:
                    self._segment_steps.append((name, repeat))
            else:
                self._segment_steps = []
                raise ValueError(f"Segment {name} is not defined.")
        self._segment_steps.append(("__end", 1))

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
                next_step = step_number + 1
                end = "end_sequence"
            else:
                next_step = step_number + 1
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
