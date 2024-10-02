import copy
import time
from typing import Any

import numpy as np

from onix.control import bin_and_average_absorption_data, group_data_by_detects, try_get_next_edf_to_run, clear_pending_edfs
from onix.control.devices import m4i, dg, quarto_e_field
from onix.control.hardware import AWG_BOARD_COUNT
from onix.control.segments import AllBoardSegments, Segment
from onix.control.segment_builder import name_to_segment_builder
from onix.data_tools import save_experiment_data
from onix.headers.awg.m4i6622 import M4i6622
from onix.headers.digitizer.digitizer import Digitizer
from onix.headers.quarto_e_field import Quarto
from onix.units import ureg


class ExpSequence:
    """Converts experiment sequence steps to AWG segments.
    
    Experiment contains a series of sequence steps that represent corresponding physics.
    Each experiment sequence step contains one or more AWG segments, each of them represent a block
    of data to be output by the AWG.

    Args:
        exp_sequence: list of strs, experiment sequence steps. Each step must start with an allowed
            step name, see `name_to_segment_builder`.
        parameters: dict, experiment parameters.
        parameters_to_iterate: list of tuple of strs, paths to the parameters to iterate. For
            example, if the LF detuning and LF phase of a Ramsey sequence are scanned, it should be
            `[("lf", "ramsey", "detuning"), ("lf", "ramsey", "phase")].
        iterate_parameter_values: list of tuple of any types, parameter values to iterate over. For
            example, for a scan of the LF detuning between [10, 10] kHz, and a phase scan between
            [0, pi], it should be `[(10 * ureg.kHz, 0), (10 * ureg.kHz, np.pi), (-10 * ureg.kHz, 0),
            (-10 * ureg.kHz, np.pi)]`.
    """
    def __init__(
        self,
        exp_sequence: list[str],
        parameters: dict[str, Any],
        parameters_to_iterate: list[tuple[str, ...]] = None,
        iterate_parameter_values: list[tuple[Any, ...]] = None,
    ):
        self._exp_sequence = exp_sequence
        self._parameters = parameters
        if parameters_to_iterate is None:
            parameters_to_iterate = []
        self._parameters_to_iterate = parameters_to_iterate
        if iterate_parameter_values is None:
            iterate_parameter_values = []
        self._iterate_parameter_values = iterate_parameter_values
        self._all_board_segments = AllBoardSegments(AWG_BOARD_COUNT)

        self._build_all_segments_and_steps()

    def _get_parameter_after_iteration(self, iteration_index: int) -> dict[str, Any]:
        parameters = copy.deepcopy(self._parameters)
        for kk, parameter_to_iterate in enumerate(self._parameters_to_iterate):
            parameters_path = parameters
            for parameter_step in parameter_to_iterate[:-1]:
                parameters_path = parameters_path[parameter_step]
            parameters_path[parameter_to_iterate[-1]] = self._iterate_parameter_values[iteration_index][kk]
        return parameters

    def _build_all_segments_and_steps(self):
        # TODO: improve local variable names in this function.
        # dict mapping experiment sequence steps to list of Segments and steps.
        self._segment_and_steps: dict[str, list[tuple[Segment, int]]] = {}
        # dict mapping experiment sequence steps to parameters that would scan this step if iterated.
        iterated_parameters: dict[str, list[tuple[str]]] = {}
        for name in self._exp_sequence:
            self._segment_and_steps[name], iterated_parameters[name] = self._build_segments(
                name, self._parameters
            )

        segments_to_iterate_over: dict[str, dict[int, list[Segment]]] = {}
        for name in iterated_parameters:
            # parameters that iterates and scans this step
            overlap_parameters = set(iterated_parameters[name]).intersection(self._parameters_to_iterate)
            if len(overlap_parameters) > 0:
                segments_to_iterate_over[name] = {}
                overlap_parameter_values = {}
                for kk, parameter_values in enumerate(self._iterate_parameter_values):
                    parameters_overriden = self._get_parameter_after_iteration(kk)
                    this_iteration_overlap_parameter_values = []
                    for overlap_parameter in overlap_parameters:
                        overlap_parameter_index = self._parameters_to_iterate.index(overlap_parameter)
                        this_iteration_overlap_parameter_values.append(parameter_values[overlap_parameter_index])
                    this_iteration_overlap_parameter_values = tuple(this_iteration_overlap_parameter_values)
                    if this_iteration_overlap_parameter_values not in overlap_parameter_values.values():
                        overlap_parameter_values[kk] = this_iteration_overlap_parameter_values
                        # build and add sequence
                        segments_to_iterate_over[name][kk], _ = self._build_segments(
                            f"{name}_{kk}", parameters_overriden
                        )
                        segments_to_iterate_over[name][kk] = [ll for (ll, _) in segments_to_iterate_over[name][kk]]
                    else:
                        index = list(overlap_parameter_values.values()).index(this_iteration_overlap_parameter_values)
                        segments_to_iterate_over[name][kk] = segments_to_iterate_over[name][index]

        segment_steps = []
        time_now = 0 * ureg.s
        rise_times = []
        fall_times = []
        last_segment_on = False
        for name in self._exp_sequence:
            for seg, steps in self._segment_and_steps[name]:
                self._all_board_segments.add_segment(seg)
                segment_steps.append((seg.name, steps))
                if seg.field_on:
                    if not last_segment_on:
                        rise_times.append(time_now)
                    last_segment_on = True
                else:
                    if last_segment_on:
                        fall_times.append(time_now)
                    last_segment_on = False
                time_now += seg.actual_duration * steps
        self.E_field_rise_and_fall_times = zip(rise_times, fall_times)

        segments_to_replace = []
        segments_to_loop_over = [[] for kk in range(len(self._iterate_parameter_values))]
        for name in segments_to_iterate_over:
            segments_to_replace.extend([seg.name for seg, steps in self._segment_and_steps[name]])
            for iter_index in segments_to_iterate_over[name]:
                for seg in segments_to_iterate_over[name][iter_index]:
                    self._all_board_segments.add_segment(seg)
                    segments_to_loop_over[iter_index].append(seg.name)
        segments_to_replace = tuple(segments_to_replace)
        segments_to_loop_over = [tuple(kk) for kk in segments_to_loop_over]
    
        if len(self._iterate_parameter_values) > 0:
            if len(segments_to_replace) == 0:
                segments_to_replace = (None, )
                segments_to_loop_over = [(None, ) for kk in range(len(self._iterate_parameter_values))]
            self._all_board_segments.setup_loops(
                segments_to_replace, segments_to_loop_over,
            )
        self._all_board_segments.setup_sequence(segment_steps)

    def _build_segments(
        self,
        sequence_step_name: str,
        parameters: dict[str, Any],
    ) -> tuple[list[tuple[Segment, int]], list[tuple[str]]]:
        for match_name, segment_builder_func in name_to_segment_builder.items():
            if sequence_step_name.startswith(match_name):
                return segment_builder_func(sequence_step_name, parameters)
        raise ValueError(f"Invalid sequence step name {sequence_step_name}.")

    @property
    def all_board_segments(self) -> AllBoardSegments:
        return self._all_board_segments

    @property
    def segment_and_steps(self) -> dict[str, list[tuple[Segment, int]]]:
        return self._segment_and_steps

    def digitizer_info(self):
        dg_params = self._parameters["digitizer"]
        detect_params = {"repeats": {}}
        for name in self.segment_and_steps:
            if name.startswith("detect"):
                for seg, steps in self.segment_and_steps[name]:
                    if seg.name.startswith("detect"):
                        detect_params["repeats"][name] = steps
                        for kk in seg.additional_detection_parameters:
                            detect_params[kk] = seg.additional_detection_parameters[kk]
        return (dg_params, detect_params)


class SingleExpExecutor:
    """Programs the AWG and digitizer, executes an experiment."""
    def __init__(
        self,
        awg: M4i6622,
        quarto: Quarto,
        digitizer: Digitizer,
        name: str,
        exp_sequence: ExpSequence,
        skip_awg_programming: bool = False,
        skip_digitizer_programming: bool = False,
        run_first_card_only: bool = False,
        stop_first_card_only: bool = False,
    ):
        self._awg = awg
        self._quarto = quarto
        self._digitizer = digitizer
        self._name = name
        self._exp_sequence = exp_sequence
        self._run_first_card_only = run_first_card_only
        self._stop_first_card_only = stop_first_card_only
        self._dg_params, self._detect_params = self._exp_sequence.digitizer_info()
        self._data = None

        if not skip_awg_programming:
            self.setup_awg()
        if not skip_digitizer_programming:
            self.setup_digitizer()
        self.setup_quarto_amplitudes()
        self.run()
        self.save_data()

    def setup_awg(self):
        self._awg.setup_segments(self._exp_sequence.all_board_segments)
        quarto_e_field.remove_all_pulses()
        for rise_time, fall_time in self._exp_sequence.E_field_rise_and_fall_times:
            quarto_e_field.add_pulse(rise_time, fall_time)
        field_plate_params = self._exp_sequence._parameters["field_plate"]
        quarto_e_field.rise_ramp_time(field_plate_params["rise_ramp_time"])
        quarto_e_field.fall_ramp_time(field_plate_params["fall_ramp_time"])

    def setup_digitizer(self):
        num_channels = self._dg_params["num_channels"]
        sample_rate = self._dg_params["sample_rate"]
        segment_repeats = sum(self._detect_params["repeats"].values())
        segment_duration = self._detect_params["duration"].to("s").magnitude

        self._digitizer.set_acquisition_config(
            num_channels=num_channels,
            sample_rate=sample_rate,
            segment_size=int(segment_duration * sample_rate),
            segment_count=segment_repeats,
        )
        self._digitizer.set_channel_config(channel=1, range=self._dg_params["ch1_range"])
        if num_channels > 1:
            self._digitizer.set_channel_config(channel=2, range=self._dg_params["ch2_range"])
        self._digitizer.set_trigger_source_edge()
        self._digitizer.write_configs_to_device()

    def setup_quarto_amplitudes(self):
        field_plate_params = self._exp_sequence._parameters["field_plate"]
        quarto_e_field.V_low(field_plate_params["low_voltage"])
        quarto_e_field.V_high(field_plate_params["high_voltage"])

    def run(self):
        self._digitizer.start_capture()
        # digitizer needs some time after start capture before it can be triggered.
        DIGITIZER_ENABLE_TRIGGER_TIME = 0.01
        time.sleep(DIGITIZER_ENABLE_TRIGGER_TIME)
        self._awg.start_sequence(self._run_first_card_only)
        self._awg.wait_for_sequence_complete(self._stop_first_card_only)
        self._awg.stop_sequence(self._stop_first_card_only)

        DIGITIZER_DATA_TIMEOUT = 1
        self._digitizer.wait_for_data_ready(DIGITIZER_DATA_TIMEOUT)
        sample_rate, digitizer_data = self._digitizer.get_data()
        self._parse_digitizer_data(sample_rate, digitizer_data)

    def _parse_absorption_data(self, sample_rate: float, data: np.ndarray):
        # data is a 2D array of time_series_data * digitizer segments
        averaged_data = bin_and_average_absorption_data(
            data, sample_rate, self._detect_params["pulse_times"]
        )
        # averaged_data is a 2D array of data_for_each_optical_freq * digitizer segments
        grouped_data = group_data_by_detects(
            averaged_data, self._detect_params["repeats"]
        )
        # grouped_data is averaged_data splitted in detect_1, detect_2, etc.
        return grouped_data

    def _parse_digitizer_data(self, sample_rate: float, digitizer_data: np.ndarray):
        mode = self._detect_params["mode"]
        if mode == "abs":
            transmission = self._parse_absorption_data(sample_rate, digitizer_data[0])
            self._data = {"transmission": transmission}
            self._data["detunings_MHz"] = self._detect_params["detunings"].to("MHz").magnitude
            if self._dg_params["num_channels"] == 2:
                monitor = self._parse_absorption_data(sample_rate, digitizer_data[1])
                self._data["monitor"] = monitor
        elif mode == "fid":
            raise NotImplementedError("FID data saving is not defined.")
        else:
            raise NotImplementedError(f"Detect mode {mode} is not defined.")

    def save_data(self):
        headers = {
            "exp_sequence": self._exp_sequence._exp_sequence,
            "params": self._exp_sequence._parameters,
        }
        self.data_id = save_experiment_data(
            self._name,
            self._data,
            headers,
        )


class ExpExecutor:
    """Monitors an directory for new experiment definition files and runs them."""
    def __init__(
        self,
        awg: M4i6622,
        quarto: Quarto,
        digitizer: Digitizer,
    ):
        clear_pending_edfs()
        self._awg = awg
        self._quarto = quarto
        self._digitizer = digitizer
        self.loop()

    def loop(self):
        while True:
            time.sleep(0.01)
            edf_index, edf = try_get_next_edf_to_run()
            if edf is not None:
                exp_sequence = ExpSequence(
                    edf["exp_sequence"],
                    edf["parameters"],
                    edf["parameters_to_iterate"],
                    edf["iterate_parameter_values"],
                )
                single_exe = SingleExpExecutor(
                    self._awg,
                    self._quarto,
                    self._digitizer,
                    edf["name"],
                    exp_sequence,
                    edf["skip_awg_programming"],
                    edf["skip_digitizer_programming"],
                    edf["run_first_card_only"],
                    edf["stop_first_card_only"],
                )
                print(f"EDF #{edf_index} finished, data #{single_exe.data_id}.")


if __name__ == "__main__":
    executor = ExpExecutor(m4i, quarto_e_field, dg)
