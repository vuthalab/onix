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
from onix.models.hyperfine import states
from onix.units import Q_
from onix.headers.awg.M4i6622 import M4i6622
from onix.headers.digitizer import Digitizer
from onix.helpers import nostdout


class AntiholeEO(Sequence):
    def __init__(
        self,
        probe_transition: str,
        eo_channel: int,
        eo_offset_frequency: Union[float, Q_],
        switch_aom_channel: int,
        switch_aom_frequency: Union[float, Q_],
        switch_aom_amplitude: int,
        repeats: int,
    ):
        super().__init__(4, [0])
        self._probe_transition = probe_transition
        self._all_transitions = ["ac", "ca", "bb"]
        if probe_transition not in self._all_transitions:
            raise ValueError(f"Probe channel {probe_transition} is not defined.")
        self._pump_transitions = self._all_transitions.copy()
        self._pump_transitions.remove(probe_transition)
        self._eo_channel = eo_channel
        self._eo_offset_frequency = eo_offset_frequency
        self._switch_aom_channel = switch_aom_channel
        self._switch_aom_frequency = switch_aom_frequency
        self._switch_aom_amplitude = switch_aom_amplitude
        self._build_aom_pulse()
        self._repeats = repeats

    def _build_aom_pulse(self):
        self._switch_aom_pulse = AWGSinePulse(
            self._switch_aom_frequency, self._switch_aom_amplitude
        )

    def add_burns(self, burn_width: Union[float, Q_], burn_time: Union[float, Q_], burn_amplitude: int):
        if isinstance(burn_time, Q_):
            burn_time = burn_time.to("s").magnitude
        burn_piecewise_time = 0.1
        self._burn_counts = 1
        if burn_time > burn_piecewise_time:
            self._burn_counts = int(burn_time / burn_piecewise_time) + 1
            burn_time = burn_piecewise_time
        for name in self._all_transitions:
            F_state = name[0]
            D_state = name[1]
            frequency = states["5D0"][D_state] - states["7F0"][F_state] + self._eo_offset_frequency
            lower_limit = frequency - burn_width / 2
            upper_limit = frequency + burn_width / 2
            print(name, "burn", lower_limit, upper_limit)
            segment = Segment(f"burn_{name}", burn_piecewise_time)
            segment.add_awg_function(self._switch_aom_channel, self._switch_aom_pulse)
            segment.add_awg_function(self._eo_channel, AWGSineSweep(lower_limit, upper_limit, burn_amplitude, 0, burn_piecewise_time))
            self.add_segment(segment.name, segment)

    def add_pumps(self, pump_time: Union[float, Q_], pump_amplitude: int):
        if isinstance(pump_time, Q_):
            pump_time = pump_time.to("s").magnitude
        pump_piecewise_time = 0.1
        self._pump_counts = 1
        if pump_time > pump_piecewise_time:
            self._pump_counts = int(pump_time / pump_piecewise_time) + 1
            pump_time = pump_piecewise_time
        for name in self._pump_transitions:
            F_state = name[0]
            D_state = name[1]
            frequency = states["5D0"][D_state] - states["7F0"][F_state] + self._eo_offset_frequency
            print(name, "pump", frequency)
            segment = Segment(f"pump_{name}", pump_piecewise_time)
            segment.add_awg_function(self._switch_aom_channel, self._switch_aom_pulse)
            segment.add_awg_function(self._eo_channel, AWGSinePulse(frequency, pump_amplitude))
            self.add_segment(segment.name, segment)

    def add_probe(
        self,
        probe_detunings: Union[List[float], Q_],
        probe_amplitude: float,
        aom_probe_amplitude: float,
        on_time: Union[float, Q_],
        off_time: Union[float, Q_],
        ttl_probe_offset_time: Optional[Union[float, Q_]] = 4e-6,
        ttl_start_time: Optional[Union[float, Q_]] = 12e-6,
        ttl_duration: Optional[Union[float, Q_]] = 4e-6,
    ):
        if isinstance(on_time, Q_):
            on_time = on_time.to("s").magnitude
        if isinstance(off_time, Q_):
            off_time = off_time.to("s").magnitude
        if isinstance(ttl_probe_offset_time, Q_):
            ttl_probe_offset_time = ttl_probe_offset_time.to("s").magnitude
        if isinstance(ttl_start_time, Q_):
            ttl_start_time = ttl_start_time.to("s").magnitude
        if isinstance(ttl_duration, Q_):
            ttl_duration = ttl_duration.to("s").magnitude
        F_state = self._probe_transition[0]
        D_state = self._probe_transition[1]
        probe_frequencies = states["5D0"][D_state] - states["7F0"][F_state] + self._eo_offset_frequency + probe_detunings
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
            on_time, off_time, [self._switch_aom_frequency] * len(probe_frequencies), aom_probe_amplitude, start_time=start_time
        )
        segment.add_awg_function(self._switch_aom_channel, ao_function)
        segment._duration = segment.duration + ttl_probe_offset_time
        self.add_segment(segment.name, segment)

        self.probe_read_time = segment.duration - ttl_start_time

    def add_break(self, break_time: Optional[Union[float, Q_]] = 10e-6):
        segment = SegmentEmpty("empty", break_time)
        self.add_segment("break", segment)

    def setup_sequence(self, probe_repeats: int = 1):
        self._probe_repeats = probe_repeats
        segment_repeats = []
        segment_repeats.append(("probe", probe_repeats))
        segment_repeats.append(("break", 1))

        for kk in range(self._burn_counts):
            for name in self._all_transitions:
                segment_repeats.append((f"burn_{name}", 1))

        segment_repeats.append(("break", 10000))
        segment_repeats.append(("probe", probe_repeats))
        segment_repeats.append(("break", 1))

        for kk in range(self._pump_counts):
            for name in self._pump_transitions:
                segment_repeats.append((f"pump_{name}", 1))
                segment_repeats.append(("break", 1))

        segment_repeats.append(("break", 10000))
        segment_repeats.append(("probe", probe_repeats))
        segment_repeats.append(("break", 1))
        return super().setup_sequence(segment_repeats)

    def setup_m4i(self):
        self.m4i = M4i6622(
            channelNum=self._awg_channel_num,
            sequenceReplay=True,
            loop_list=self.segment_loops,
            next=self.segment_next,
            conditions=self.segment_conditions,
            initialStep=0,
            segTimes=self.segment_durations,
            ttlOutOn=self.ttl_out_on,
            ttlOutChannel=self._ttl_channels,
            verbose=True,
        )
        self.m4i.setSoftwareBuffer()
        self.m4i.configSequenceReplay(
            segFunctions=self.segment_awg_functions,
            steps=self.segment_steps,
            ttlFunctionList=self.segment_ttl_functions,
        )

    def setup_digitizer(
        self,
        ip: str,
        sampling_rate: int = 1e7,
    ):
        self.sampling_rate = int(sampling_rate)
        with nostdout():
            try:
                self.dg = Digitizer(ip)
                self.dg.list_errors()
            except Exception:
                self.dg = Digitizer(ip)

        params_dict = {
            "num_samples": int(self.probe_read_time * self.sampling_rate),
            "sampling_rate": self.sampling_rate,
            "ch1_voltage_range": 1,
            "ch2_voltage_range": 1,
            "trigger_channel": 0,
            "data_format": "float32",
            "coupling": "DC",
            "num_records": self._repeats * self._probe_repeats * 3,
            "triggers_per_arm": self._repeats * self._probe_repeats * 3,
        }
        self.dg.set_parameters(params_dict)
        self.dg.configure()
        self.dg.set_two_channel_waitForTrigger()
