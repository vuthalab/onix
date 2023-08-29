from typing import List, Dict, Tuple, Optional, Union, Callable, Any
from units import Q_, ureg

from sequences.sequence import (
    Sequence,
    Segment,
    SegmentEmpty,
    AWGSinePulse,
    AWGSineSweep,
    AWGSineTrain,
    TTLOff,
    TTLOn,
    TTLPulses,
)


class SegmentBurn(Segment):
    def __init__(self, name: str, duration: Union[float, Q_], parameters: Dict[int, Dict[str, Union[float, Q_]]]):
        super().__init__(name, duration)
        for channel in parameters:
            f_start = parameters[channel]["f_start"]
            f_stop = parameters[channel]["f_stop"]
            amplitude = parameters[channel]["amplitude"]
            start_time = 0
            end_time = self._duration
            function = AWGSineSweep(f_start, f_stop, amplitude, start_time, end_time)
            self.add_awg_function(channel, function)
        self.fill_all_channels()


class SegmentPump(Segment):
    def __init__(self, name: str, duration: Union[float, Q_], parameters: Dict[int, Dict[str, Union[float, Q_]]]):
        super().__init__(name, duration)
        for channel in parameters:
            frequency = parameters[channel]["frequency"]
            amplitude = parameters[channel]["amplitude"]
            function = AWGSinePulse(frequency, amplitude)
            self.add_awg_function(channel, function)
        self.fill_all_channels()


class SegmentPumpSweep(Segment):
    def __init__(self, name: str, duration: Union[float, Q_], parameters: Dict[int, Dict[str, Union[float, Q_]]]):
        super().__init__(name, duration)
        for channel in parameters:
            f_start = parameters[channel]["f_start"]
            f_stop = parameters[channel]["f_stop"]
            amplitude = parameters[channel]["amplitude"]
            start_time = 0
            end_time = self._duration
            awg_function = AWGSineSweep(f_start, f_stop, amplitude, start_time, end_time)
            self.add_awg_function(channel, awg_function)
        self.fill_all_channels()


class SegmentProbe(Segment):
    def __init__(
        self,
        name: str,
        channel: int,
        digitizer_ttl_channel: int,
        frequencies: Union[List[float], Q_],
        amplitudes: Union[float, List[float], Q_],
        on_time: Union[float, Q_],
        off_time: Union[float, Q_],
        ttl_start_time: Union[float, Q_],
        ttl_duration: Union[float, Q_],
        sequence_ttl_offset_time: Union[float, Q_],
    ):
        super().__init__(name, duration=None)
        ttl_stop_time = ttl_start_time + ttl_duration
        ttl_function = TTLPulses([[ttl_start_time, ttl_stop_time]])
        self.add_ttl_function(digitizer_ttl_channel, ttl_function)
        start_time = ttl_start_time + sequence_ttl_offset_time
        awg_function = AWGSineTrain(
            on_time, off_time, frequencies, amplitudes, start_time=start_time
        )
        self.add_awg_function(channel, awg_function)
