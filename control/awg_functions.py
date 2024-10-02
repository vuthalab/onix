from functools import partial
from typing import Optional, Union
import numbers

import numpy as np
from onix.units import Q_, ureg


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

class AWGRamp(AWGFunction):
    def __init__(
        self,
        start_amplitude: float,
        end_amplitude: float,
        start_time: Union[float, Q_],
        end_time: Union[float, Q_],
    ):
        super().__init__()
        self._start_amplitude = start_amplitude
        self._end_amplitude = end_amplitude
        self._start_time = start_time
        self._end_time = end_time

    def output(self, times):
        def constant(amplitude, times):
            return np.ones(len(times)) * amplitude

        start_time = float(self._start_time.to("s").magnitude)
        end_time = float(self._end_time.to("s").magnitude)
        def ramp(times):
            slope = (self._end_amplitude - self._start_amplitude) / (end_time - start_time)
            return self._start_amplitude + slope * (times - self._start_time)

        funclist = []
        condlist = []
        funclist.append(partial(constant, self._start_amplitude))
        condlist.append(times <= start_time)
        funclist.append(partial(constant, self._end_amplitude))
        condlist.append(times > end_time)
        funclist.append(ramp)
        return np.piecewise(times, condlist, funclist)

    @property
    def min_duration(self) -> Q_:
        return self._end_time

    @property
    def max_amplitude(self):
        return np.max([self._start_amplitude, self._end_amplitude])


class AWGHalfSineRamp(AWGRamp):
    def output(self, times):
        def constant(amplitude, times):
            return np.ones(len(times)) * amplitude

        start_time = float(self._start_time.to("s").magnitude)
        end_time = float(self._end_time.to("s").magnitude)

        def ramp(times):
            ramp_time = end_time - start_time
            ramp_amplitude = self._end_amplitude - self._start_amplitude
            return np.sin(np.pi * (times - start_time) / (2 * ramp_time)) * ramp_amplitude + self._start_amplitude

        funclist = []
        condlist = []
        funclist.append(partial(constant, self._start_amplitude))
        condlist.append(times <= start_time)
        funclist.append(partial(constant, self._end_amplitude))
        condlist.append(times > end_time)
        funclist.append(ramp)
        return np.piecewise(times, condlist, funclist)


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
    
class AWGTwoSinePulse(AWGFunction):
    def __init__(
        self,
        frequency1: Union[float, Q_],
        frequency2: Union[float, Q_],
        amplitude: float,
        phase: float = 0,
        start_time: Optional[Union[float, Q_]] = None,
        end_time: Optional[Union[float, Q_]] = None,
    ):
        super().__init__()
        if isinstance(frequency1, numbers.Number):
            frequency1 = frequency1 * ureg.Hz
        self._frequency1: Q_ = frequency1
        if isinstance(frequency2, numbers.Number):
            frequency2 = frequency2 * ureg.Hz
        self._frequency2: Q_ = frequency2
        self._amplitude = amplitude # divide by two so doesn't go past max allowable amplitude with 2 sinusoids
        self._phase = phase
        if isinstance(start_time, numbers.Number):
            start_time = start_time * ureg.s
        self._start_time: Union[Q_, None] = start_time
        if isinstance(end_time, numbers.Number):
            end_time = end_time * ureg.s
        self._end_time: Union[Q_, None] = end_time

    def output(self, times):
        frequency1 = self._frequency1.to("Hz").magnitude
        frequency2 = self._frequency2.to("Hz").magnitude
        sine = self._amplitude * (np.sin(2 * np.pi * frequency1 * times + self._phase) + np.sin(2 * np.pi * frequency2 * times + self._phase))
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


class AWGSimultaneousSinePulses(AWGFunction):
    def __init__(
        self,
        frequencies: Union[float, list[float], Q_, list[Q_]],
        amplitude: float,
        phase: float = 0,
        start_time: Optional[Union[float, Q_]] = None,
        end_time: Optional[Union[float, Q_]] = None,
    ):
        super().__init__()
        if isinstance(frequencies, numbers.Number):
            frequencies = frequencies * ureg.Hz
        elif not isinstance(frequencies, Q_):
            for kk in range(len(frequencies)):
                if isinstance(frequencies[kk], numbers.Number):
                    frequencies[kk] = frequencies[kk] * ureg.Hz
            frequencies = Q_.from_list(frequencies, "Hz")
        self._frequencies: Q_ = frequencies
        self._amplitude = amplitude
        self._phase = phase
        if isinstance(start_time, numbers.Number):
            start_time = start_time * ureg.s
        self._start_time: Union[Q_, None] = start_time
        if isinstance(end_time, numbers.Number):
            end_time = end_time * ureg.s
        self._end_time: Union[Q_, None] = end_time

    def output(self, times):
        frequencies = self._frequencies.to("Hz").magnitude
        sine = np.sum([self._amplitude * np.sin(2 * np.pi * frequency * times + self._phase) for frequency in frequencies], axis=1) # possible error; this might need to be axis = 0
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
        return self._amplitude*len(self._frequencies)
    

class AWGProductSinePulses(AWGFunction):
    def __init__(
        self,
        frequencies: Union[float, list[float], Q_, list[Q_]],
        amplitude: float,
        phase: float = 0,
        start_time: Optional[Union[float, Q_]] = None,
        end_time: Optional[Union[float, Q_]] = None,
    ):
        super().__init__()
        if isinstance(frequencies, numbers.Number):
            frequencies = frequencies * ureg.Hz
        elif not isinstance(frequencies, Q_):
            for kk in range(len(frequencies)):
                if isinstance(frequencies[kk], numbers.Number):
                    frequencies[kk] = frequencies[kk] * ureg.Hz
            frequencies = Q_.from_list(frequencies, "Hz")
        self._frequencies: Q_ = frequencies
        self._amplitude = amplitude
        self._phase = phase
        if isinstance(start_time, numbers.Number):
            start_time = start_time * ureg.s
        self._start_time: Union[Q_, None] = start_time
        if isinstance(end_time, numbers.Number):
            end_time = end_time * ureg.s
        self._end_time: Union[Q_, None] = end_time

    def output(self, times):
        frequencies = self._frequencies.to("Hz").magnitude
        sine = self._amplitude * np.prod([ np.sin(2 * np.pi * frequency * times + self._phase) for frequency in frequencies], axis=0)
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

class AWGDoubleSineSweep(AWGFunction):
    def __init__(
        self,
        start_frequency_1: Union[float, Q_],
        stop_frequency_1: Union[float, Q_],
        amplitude_1: float,
        start_frequency_2: Union[float, Q_],
        stop_frequency_2: Union[float, Q_],
        amplitude_2: float,
        start_time: Union[float, Q_],
        end_time: Union[float, Q_],
        phase: float = 0,
    ):
        super().__init__()
        if isinstance(start_frequency_1, numbers.Number):
            start_frequency_1 = start_frequency_1 * ureg.Hz
        self._start_frequency_1: Q_ = start_frequency_1
        if isinstance(stop_frequency_1, numbers.Number):
            stop_frequency_1 = stop_frequency_1 * ureg.Hz
        self._stop_frequency_1: Q_ = stop_frequency_1
        self._amplitude_1 = amplitude_1
        if isinstance(start_frequency_2, numbers.Number):
            start_frequency_2 = start_frequency_2 * ureg.Hz
        self._start_frequency_2: Q_ = start_frequency_2
        if isinstance(stop_frequency_2, numbers.Number):
            stop_frequency_2 = stop_frequency_2 * ureg.Hz
        self._stop_frequency_2: Q_ = stop_frequency_2
        self._amplitude_2 = amplitude_2
        if isinstance(start_time, numbers.Number):
            start_time = start_time * ureg.s
        self._start_time: Q_ = start_time
        if isinstance(end_time, numbers.Number):
            end_time = end_time * ureg.s
        self._end_time: Q_ = end_time
        self._phase = phase

    def output(self, times):
        """Scanning half of the frequency is actually scanning the full range."""
        start_frequency = self._start_frequency_1.to("Hz").magnitude
        stop_frequency = self._stop_frequency_1.to("Hz").magnitude
        start_time = self._start_time.to("s").magnitude
        end_time = self._end_time.to("s").magnitude
        duration = end_time - start_time
        frequency_scan = stop_frequency - start_frequency
        instant_frequencies = (
            times - start_time
        ) / duration * frequency_scan / 2 + start_frequency
        sine_sweep_1 = self._amplitude_1 * np.sin(
            2 * np.pi * instant_frequencies * times + self._phase
        )
        start_frequency = self._start_frequency_2.to("Hz").magnitude
        stop_frequency = self._stop_frequency_2.to("Hz").magnitude
        start_time = self._start_time.to("s").magnitude
        end_time = self._end_time.to("s").magnitude
        duration = end_time - start_time
        frequency_scan = stop_frequency - start_frequency
        instant_frequencies = (
            times - start_time
        ) / duration * frequency_scan / 2 + start_frequency
        sine_sweep_2 = self._amplitude_2 * np.sin(
            2 * np.pi * instant_frequencies * times + self._phase
        )
        mask_start = np.heaviside(times - start_time, 0)
        mask_end = np.heaviside(end_time - times, 1)
        return (sine_sweep_1 + sine_sweep_2) * mask_start * mask_end

    @property
    def min_duration(self) -> Q_:
        return self._end_time

    @property
    def max_amplitude(self):
        return np.max([self._amplitude_1, self._amplitude_2])

class AWGSineSweepEnveloped(AWGSineSweep):

    def sechEnvelope(self, times):
        start_time = self._start_time.to("s").magnitude
        end_time = self._end_time.to("s").magnitude
        # A0 = 0.9*np.pi
        # x0 = np.log(1 + np.tan(A0/2)) - np.log(1 - np.tan(A0/2))
        return 1/np.cosh((times - (start_time + end_time)/2)/(end_time-start_time)*8)
    
    def output(self, times):
        """Scanning half of the frequency is actually scanning the full range."""
        return self.sechEnvelope(times) * super().output(times)

class AWGSineTrain(AWGFunction):
    def __init__(
        self,
        on_time: Union[float, Q_],
        off_time: Union[float, Q_],
        frequencies: Union[float, list[float], Q_, list[Q_]],
        amplitudes: Union[float, list[float]],
        phases: Union[float, list[float]] = 0,
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

class AWGCompositePulse(AWGFunction):
    def __init__(
        self,
        durations: Union[float, list[float], Q_, list[Q_]],
        frequencies: Union[float, list[float], Q_, list[Q_]],
        amplitudes: Union[float, list[float]],
        phases: Union[float, list[float]] = 0,
        start_time: Union[float, Q_] = 0,
    ):
        super().__init__()
        if isinstance(durations, numbers.Number):
            durations = durations * ureg.s
        elif not isinstance(durations, Q_):
            for kk in range(len(durations)):
                if isinstance(durations[kk], numbers.Number):
                    durations[kk] = durations[kk] * ureg.s
            durations = Q_.from_list(durations, "s")
        self._durations: Q_ = durations
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
        frequencies = self._frequencies.to("Hz").magnitude
        for kk in range(len(frequencies)):
            end_time = start_time + self._durations[kk].to("s").magnitude
            funclist.append(
                partial(sine, frequencies[kk], self._amplitudes[kk], self._phases[kk])
            )
            condlist.append(np.logical_and(times > start_time, times <= end_time))
            start_time = end_time
        funclist.append(zero)
        return np.piecewise(times, condlist, funclist)

    @property
    def min_duration(self) -> Q_:
        return self._start_time + np.sum(self._durations)

    @property
    def max_amplitude(self):
        return np.max(self._amplitudes)

class AWGMultiFunctions(AWGFunction):
    def __init__(self, functions: list[AWGFunction], start_times: Q_, end_times: Q_):
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

class AWGDoubleSineTrain(AWGFunction):
    def __init__(
      self,
      train1_frequencies: Union[float, list[float], Q_, list[Q_]],
      train1_amplitude: float,
      train1_on_time: Union[float, Q_],
      train1_off_time: Union[float, Q_],
      delay_between_trains: Union[float, Q_],
      train2_frequencies: Union[float, list[float], Q_, list[Q_]],
      train2_amplitude: float,
      train2_on_time: Union[float, Q_],
      train2_off_time: Union[float, Q_],
      phase_difference: float,
    ):
        super().__init__()

        self._train1_amplitude = train1_amplitude
        if isinstance(train1_on_time, numbers.Number):
            train1_on_time = train1_on_time * ureg.s
        self._train1_on_time: Q_ = train1_on_time
        if isinstance(train1_off_time, numbers.Number):
            train1_off_time = train1_off_time * ureg.s
        self._train1_off_time: Q_ = train1_off_time
        if isinstance(train1_frequencies, numbers.Number):
            train1_frequencies = train1_frequencies * ureg.Hz
        elif not isinstance(train1_frequencies, Q_):
            for kk in range(len(train1_frequencies)):
                if isinstance(train1_frequencies[kk], numbers.Number):
                    train1_frequencies[kk] = train1_frequencies[kk] * ureg.Hz
            train1_frequencies = Q_.from_list(train1_frequencies, "Hz")
        self._train1_frequencies: Q_ = train1_frequencies

        if isinstance(delay_between_trains, numbers.Number):
            delay_between_trains = delay_between_trains * ureg.s
            
        self._train2_amplitude = train2_amplitude
        if isinstance(train2_on_time, numbers.Number):
            train2_on_time = train2_on_time * ureg.s
        self._delay_between_trains = delay_between_trains

        self._train2_on_time: Q_ = train2_on_time
        if isinstance(train2_off_time, numbers.Number):
            train2_off_time = train2_off_time * ureg.s
        self._train2_off_time: Q_ = train2_off_time
        if isinstance(train2_frequencies, numbers.Number):
            train2_frequencies = train2_frequencies * ureg.Hz
        elif not isinstance(train2_frequencies, Q_):
            for kk in range(len(train2_frequencies)):
                if isinstance(train2_frequencies[kk], numbers.Number):
                    train2_frequencies[kk] = train2_frequencies[kk] * ureg.Hz
            train2_frequencies = Q_.from_list(train2_frequencies, "Hz")
        self._train2_frequencies: Q_ = train2_frequencies

        self._phase_difference = phase_difference
        
        self._unify_lists()

    def _unify_lists(self):
        """Makes sure that frequencies, amplitudes, and phases are lists of the same length."""
        length = None
        try:
            self._train1_frequencies[0]
            is_list_train1_freq = True
            length = len(self._train1_frequencies)
        except Exception:
            is_list_train1_freq = False

        try:
            self._train2_frequencies[0]
            is_list_train2_freq = True
        except Exception:
            is_list_train2_freq = False
        
        if length is None:
            raise ValueError(
                "First train frequencies not a list"
            )
        
        if not is_list_train1_freq:
            frequency_value = self._train1_frequencies.to("Hz").magnitude
            self._train1_frequencies = np.repeat(frequency_value, length) * ureg.Hz
        if not is_list_train2_freq:
            frequency_value = self._train2_frequencies.to("Hz").magnitude
            self._train2_frequencies = np.repeat(frequency_value, length) * ureg.Hz


    def output(self, times):
        def sine(times, frequency, amplitude, phase, start_time, end_time):
            mask = np.heaviside(times - start_time, 1) - np.heaviside(times - end_time, 1)
            return mask * amplitude * np.sin(2 * np.pi * frequency * times + phase)
    
        data = np.zeros(len(times))

        train1_on_time = self._train1_on_time.to("s").magnitude
        train1_off_time = self._train1_off_time.to("s").magnitude
        train2_on_time = self._train2_on_time.to("s").magnitude
        train2_off_time = self._train2_off_time.to("s").magnitude

        train_1_frequencies = self._train1_frequencies.to("Hz").magnitude
        train_2_frequencies = self._train2_frequencies.to("Hz").magnitude

        delay_between_trains = self._delay_between_trains.to("s").magnitude

        start_time = 0
        for frequency in train_1_frequencies:
            end_time = start_time + train1_on_time
            data += sine(times, frequency, self._train1_amplitude, 0, start_time, end_time)
            start_time = end_time + train1_off_time
        start_time = start_time - train1_off_time + delay_between_trains

        for frequency in train_2_frequencies:
            end_time = start_time + train2_on_time
            data += sine(times, frequency, self._train2_amplitude, self._phase_difference, start_time, end_time)
            start_time = end_time + train2_off_time
        start_time = start_time - train2_off_time
        return data

    @property
    def max_amplitude(self) -> float:
        return np.max([self._train1_amplitude, self._train2_amplitude])

    @property
    def min_duration(self) -> Q_:
        times = [
            self._train1_on_time * len(self._train1_frequencies),
            self._train1_off_time * (len(self._train1_frequencies) - 1),
            self._delay_between_trains,
            self._train2_on_time * len(self._train2_frequencies),
            self._train2_off_time * (len(self._train2_frequencies) - 1),
        ]
        for i, _ in enumerate(times):
            times[i] = times[i].to("s").magnitude
        return np.sum(times) * ureg.s


class AWGFIDPulse(AWGFunction):
    def __init__(
        self,
        pump_frequencies: Union[list[float], Q_, list[Q_]],
        pump_amplitude: float,
        pump_time: Union[float, Q_],
        wait_time: Union[float, Q_],
        probe_frequency: Union[float, Q_],
        probe_amplitude: float,
        probe_time: Union[float, Q_],
        probe_phase: float,
        start_time: Optional[Union[float, Q_]],
    ):
        super().__init__()

        self._pump_amplitude = pump_amplitude
        self._probe_amplitude = probe_amplitude
        self._probe_phase = probe_phase

        if isinstance(pump_time, numbers.Number):
            pump_time = pump_time * ureg.s
        self._pump_time: Q_ = pump_time

        if isinstance(wait_time, numbers.Number):
            wait_time = wait_time * ureg.s
        self._wait_time: Q_ = wait_time

        if isinstance(probe_frequency, numbers.Number):
            probe_frequency = probe_frequency * ureg.Hz
        self._probe_frequency: Q_ = probe_frequency

        if isinstance(probe_time, numbers.Number):
            probe_time = probe_time * ureg.s
        self._probe_time: Q_ = probe_time

        if start_time is None:
            start_time = 0 * ureg.s
        if isinstance(start_time, numbers.Number):
            start_time = start_time * ureg.s
        self._start_time: Q_ = start_time

        if isinstance(pump_frequencies, numbers.Number):
            pump_frequencies = pump_frequencies * ureg.Hz
        elif not isinstance(pump_frequencies, Q_):
            for kk in range(len(pump_frequencies)):
                if isinstance(pump_frequencies[kk], numbers.Number):
                    pump_frequencies[kk] = pump_frequencies[kk] * ureg.Hz
            pump_frequencies = Q_.from_list(pump_frequencies, "Hz")
        self._pump_frequencies: Q_ = pump_frequencies

    def output(self, times):
        def sine(times, frequency, amplitude, phase, start_time, end_time):
            mask = np.heaviside(times - start_time, 1) - np.heaviside(times - end_time, 1)
            return mask * amplitude * np.sin(2 * np.pi * frequency * times + phase)
        
        data = np.zeros(len(times))

        start_time = self._start_time.to("s").magnitude
        pump_time = self._pump_time.to("s").magnitude
        for frequency in self._pump_frequencies:
            frequency = frequency.to("Hz").magnitude
            data += sine(times, frequency, self._pump_amplitude, 0, start_time, start_time + pump_time)

        probe_start_time = start_time + pump_time + self._wait_time.to("s").magnitude
        probe_stop_time = probe_start_time + self._probe_time.to("s").magnitude
        probe_frequency = self._probe_frequency.to("Hz").magnitude
        data += sine(times, probe_frequency, self._probe_amplitude, self._probe_phase, probe_start_time, probe_stop_time)

        return data

    @property
    def max_amplitude(self) -> float:
        return np.max([self._pump_amplitude, self._probe_amplitude])

    @property
    def min_duration(self) -> Q_:
        return self._pump_time + self._wait_time + self._probe_time


class AWGSimultaneousDoubleSineTrain(AWGFunction):
    def __init__(
      self,
      frequencies: Union[float, list[float], Q_, list[Q_]],
      amplitude1: float,
      amplitude2: float,
      comb_detuning: Union[float, Q_],
      phase_difference: float,
      on_time1: Union[float, Q_],
      on_time2: Union[float, Q_],
      delay: Union[float, Q_],
    ):
        super().__init__()

        self._amplitude1 = amplitude1
        self._amplitude2 = amplitude2
        self._phase_difference = phase_difference

        if isinstance(on_time1, numbers.Number):
            on_time1 = on_time1 * ureg.s
        self._on_time1: Q_ = on_time1
        
        if isinstance(on_time2, numbers.Number):
            on_time2 = on_time2 * ureg.s
        self._on_time2: Q_ = on_time2

        if isinstance(delay, numbers.Number):
            delay = delay * ureg.s
        self._delay: Q_ = delay

        if isinstance(frequencies, numbers.Number):
            frequencies = frequencies * ureg.Hz
        elif not isinstance(frequencies, Q_):
            for kk in range(len(frequencies)):
                if isinstance(frequencies[kk], numbers.Number):
                    frequencies[kk] = frequencies[kk] * ureg.Hz
            frequencies = Q_.from_list(frequencies, "Hz")
        self._frequencies: Q_ = frequencies

        if isinstance(comb_detuning, numbers.Number):
            comb_detuning = comb_detuning * ureg.Hz
        self._comb_detuning: Q_ = comb_detuning

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
        if length is None:
            raise ValueError(
                "Frequencies not a list"
            )
        if not is_list_freq:
            frequency_value = self._frequencies.to("Hz").magnitude
            self._frequencies = np.repeat(frequency_value, length) * ureg.Hz

    def output(self, times):
        def sine(times, frequency, amplitude, phase, start_time, end_time):
            mask = np.heaviside(times - start_time, 1) - np.heaviside(times - end_time, 1)
            return mask * amplitude * np.sin(2 * np.pi * frequency * times + phase)
        
        data = np.zeros(len(times))

        for frequency in self._frequencies:
            data += sine(times, frequency, self._amplitude1, 0, 0, self._on_time1)

        time = self._on_time1 + self._delay

        for frequency in self._frequencies:
            data += sine(times, frequency + self._comb_detuning, self._amplitude2, self._phase_difference, time, time + self._on_time2)

        return data

    @property
    def max_amplitude(self) -> float:
        return np.max([self._amplitude1, self._amplitude2])

    @property
    def min_duration(self) -> Q_:
        return self._on_time1 + self._on_time2 + self._delay
    
class AWGHSHPulse(AWGFunction):
    """
    See https://doi.org/10.1364/AO.50.006548 for details
    """
    def __init__(
      self,
      amplitude: float,
      T_0: Union[float, Q_],
      T_e: Union[float, Q_],
      T_ch: Union[float, Q_],
      center_frequency: Union[float, Q_], 
      scan_range: Union[float, Q_],  
    ):
        super().__init__()
        self.amplitude = amplitude

        if isinstance(T_0, numbers.Number):
            T_0 = T_0 * ureg.s
        self.T_0: Q_ = T_0

        if isinstance(T_e, numbers.Number):
            T_e = T_e * ureg.s
        self.T_e: Q_ = T_e

        if isinstance(T_ch, numbers.Number):
            T_ch = T_ch * ureg.s
        self.T_ch: Q_ = T_ch

        if isinstance(center_frequency, numbers.Number):
            center_frequency = center_frequency * ureg.Hz
        self.center_frequency: Q_ = center_frequency

        if isinstance(scan_range, numbers.Number):
            scan_range = scan_range * ureg.Hz
        self.scan_range: Q_ = scan_range
        

    def Omega(self, t):
        T_0 = self.T_0.to("s").magnitude
        T_ch = self.T_ch.to("s").magnitude
        T_e = self.T_e.to("s").magnitude

        condlist = [t <= T_0, 
                    np.logical_and(t > T_0, t <= T_0+T_ch), 
                    np.logical_and(t > T_0+T_ch, t<= T_ch + 2*T_0),
                    t > T_ch + 2*T_0]
        
        funclist_amplitudes = [lambda t: self.amplitude/np.cosh((t - T_0)/T_e),
                               self.amplitude,
                               lambda t: self.amplitude/np.cosh((t - T_0 - T_ch)/T_e),
                               0]
        instant_amplitudes = np.piecewise(t, condlist, funclist_amplitudes)
        return instant_amplitudes

    def f(self, t): 
        T_0 = self.T_0.to("s").magnitude
        T_ch = self.T_ch.to("s").magnitude
        T_e = self.T_e.to("s").magnitude
        center_frequency = self.center_frequency.to("Hz").magnitude
        scan_range = self.scan_range.to("Hz").magnitude * 2

        def int_f_1(t_prime):
            return center_frequency*t_prime - kappa*T_ch*t_prime/2 + T_e**2 * kappa * np.log(np.cosh((t_prime-T_0)/T_e))

        def int_f_2(t_prime):
            return center_frequency*t_prime + 0.5*kappa*t_prime**2 - kappa * t_prime* (T_0 + T_ch/2)
    
        def int_f_3(t_prime):
            return center_frequency*t_prime + kappa*T_ch*t_prime/2 + T_e**2 * kappa * np.log(np.cosh((T_0 + T_ch - t_prime)/T_e))
    
    
        condlist = [t <= T_0, 
                    np.logical_and(t > T_0, t <= T_0+T_ch), 
                    np.logical_and(t > T_0+T_ch, t<= T_ch + 2*T_0),
                    t > T_ch + 2*T_0]
        
        kappa = scan_range / T_ch
        funclist_frequencies = [lambda r: int_f_1(r) - int_f_1(0),
                                lambda r: int_f_1(T_0) - int_f_1(0) + int_f_2(r) - int_f_2(T_0),
                                lambda r: int_f_1(T_0) - int_f_1(0) + int_f_2(T_0 + T_ch) - int_f_2(T_0) + int_f_3(r) - int_f_3(T_0 + T_ch) ,
                                0]
        instant_frequencies = np.piecewise(t, condlist, funclist_frequencies)
        return instant_frequencies

    def output(self, times):
        return self.Omega(times) * np.sin(2*np.pi*self.f(times))
    
    @property 
    def max_amplitude(self) -> float:
        return self.amplitude
    
    @property
    def min_duration(self) -> Q_:
        return self.T_ch + 2*self.T_0

class AWGSpinEcho(AWGFunction):
    def __init__(
        self,
        piov2_time: Union[float, Q_],
        pi_time: Union[float, Q_],
        delay_time: Union[float, Q_],
        frequency: Union[float, Q_],
        amplitude: float,
        phase: float = 0,
        phase_pi: float = 0,
    ):
        super().__init__()
        if isinstance(piov2_time, numbers.Number):
            piov2_time = piov2_time * ureg.s
        if isinstance(pi_time, numbers.Number):
            pi_time = pi_time * ureg.s
        if isinstance(delay_time, numbers.Number):
            delay_time = delay_time * ureg.s
        if isinstance(frequency, numbers.Number):
            frequency = frequency * ureg.Hz
        self._piov2_time = piov2_time
        self._pi_time = pi_time
        self._delay_time = delay_time
        self._frequency = frequency
        self._amplitude = amplitude
        self._phase = phase
        self._phase_pi = phase_pi

    def output(self, times):
        def sine(frequency, amplitude, phase, times):
            return amplitude* np.sin(2 * np.pi * frequency * times + phase)

        def zero(times):
            return np.zeros(len(times))

        piov2_time = self._piov2_time.to("s").magnitude
        pi_time = self._pi_time.to("s").magnitude
        delay_time = self._delay_time.to("s").magnitude
        condlist = [
            times < piov2_time,
            np.logical_and(times >= piov2_time, times < piov2_time + delay_time),
            np.logical_and(times >= piov2_time + delay_time, times < piov2_time + delay_time + pi_time),
            np.logical_and(times >= piov2_time + delay_time + pi_time, times < piov2_time + 2 * delay_time + pi_time),
            times >= piov2_time + 2 * delay_time + pi_time,
        ]
        funclist = [
            partial(sine, self._frequency.to("Hz").magnitude, self._amplitude, 0),
            zero,
            partial(sine, self._frequency.to("Hz").magnitude, self._amplitude, self._phase_pi),
            zero,
            partial(sine, self._frequency.to("Hz").magnitude, self._amplitude, self._phase),
        ]
        return np.piecewise(times, condlist, funclist)

    @property
    def min_duration(self) -> Q_:
        return 2 * self._piov2_time + 2 * self._delay_time + self._pi_time

    @property
    def max_amplitude(self):
        return self._amplitude
