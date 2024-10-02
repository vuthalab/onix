from functools import partial
from typing import Union

import numpy as np
from onix.units import Q_, ureg


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
    def __init__(self, on_times: Union[list[Union[list[Union[float, Q_]], Q_]], Q_]):
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
    def __init__(self, functions: list[TTLFunction], start_times: Q_, end_times: Q_):
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
