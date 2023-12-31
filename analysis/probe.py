from typing import Any, Dict, List, Literal, Optional
import numpy as np


class Probe:
    def __init__(self, times: np.ndarray, transmissions: np.ndarray, repeats: Dict[str, int], monitors: Optional[np.ndarray] = None):
        self.times = times
        self._transmissions = transmissions
        self._monitors = monitors
        self._repeats = repeats
        self.transmission_groups = {}
        self.monitor_groups = {}
        if self._monitors is None:
            self._monitors = np.copy(self._transmissions)
        self._group_data()

    def _group_data(self):
        total_repeats = sum(self._repeats.values())
        remainder_to_group = []
        counter = 0
        for name in self._repeats:
            self.transmission_groups[name] = []
            self.monitor_groups[name] = []
            for kk in range(self._repeats[name]):
                remainder_to_group.append((counter, name))
                counter += 1
        remainder_to_group = dict(remainder_to_group)
        for kk in range(int(len(self._transmissions) / total_repeats)):
            for name in self.transmission_groups:
                self.transmission_groups[name].append([])
                self.monitor_groups[name].append([])
            for remainder in remainder_to_group:
                name = remainder_to_group[remainder]
                self.transmission_groups[name][-1].append(
                    self._transmissions[kk * total_repeats + remainder]
                )
                self.monitor_groups[name][-1].append(
                    self._monitors[kk * total_repeats + remainder]
                )
        for name in self.transmission_groups:
            self.transmission_groups[name] = np.array(self.transmission_groups[name])
            self.monitor_groups[name] = np.array(self.monitor_groups[name])

    def set_probe_times(
        self,
        pre_probe_delay: float,
        on_time: float,
        off_time: float,
        rise_delay: float,
        fall_delay: float,
        probes: Optional[List[Any]] = None,
    ):
        num_of_probes = int((max(self.times) - pre_probe_delay - fall_delay) / (on_time + off_time))
        if probes is None:
            probes = np.arange(num_of_probes)
        elif len(probes) > num_of_probes:
            raise ValueError("Probe definitions are not correct.")
        self.probes = probes

        self._probe_masks = []
        start_time = pre_probe_delay
        for kk in self.probes:
            self._probe_masks.append(
                np.bitwise_and(
                    self.times > start_time + rise_delay,
                    self.times <= start_time + on_time + fall_delay
                )
            )
            start_time += on_time + off_time
        self._calculate_statistics()

    def _calculate_statistics(self):
        self._averages = {}
        self._standard_errors = {}
        self._normalized_averages = {}
        self._normalized_standard_errors = {}
        for name in self.transmission_groups:
            group = self.transmission_groups[name]
            monitor_group = self.monitor_groups[name]
            self._averages[name] = []
            self._standard_errors[name] = []
            self._normalized_averages[name] = []
            self._normalized_standard_errors[name] = []
            for repeat in range(len(group)):
                repeat_avg = []
                repeat_ste = []
                normalized_repeat_avg = []
                normalized_repeat_ste = []
                for probe_repeat in range(len(group[repeat])):
                    probe_repeat_avg = []
                    probe_repeat_ste = []
                    normalized_probe_repeat_avg = []
                    normalized_probe_repeat_ste = []
                    for probe_index in range(len(self.probes)):
                        data = group[repeat][probe_repeat][self._probe_masks[probe_index]]
                        monitor_data = monitor_group[repeat][probe_repeat][self._probe_masks[probe_index]]
                        probe_repeat_avg.append(np.average(data))
                        probe_repeat_ste.append(np.std(data) / np.sqrt(len(data) - 1))
                        normalized_probe_repeat_avg.append(np.average(data) / np.average(monitor_data))
                        term1 = (np.std(data) / np.sqrt(len(data) - 1)) / np.average(monitor_data)
                        term2 = np.average(data) * (np.std(monitor_data) / np.sqrt(len(monitor_data) - 1)) / np.average(monitor_data) ** 2
                        normalized_probe_repeat_ste.append(np.sqrt(term1 ** 2 + term2 ** 2))
                    repeat_avg.append(probe_repeat_avg)
                    repeat_ste.append(probe_repeat_ste)
                    normalized_repeat_avg.append(normalized_probe_repeat_avg)
                    normalized_repeat_ste.append(normalized_probe_repeat_ste)
                self._averages[name].append(repeat_avg)
                self._standard_errors[name].append(repeat_ste)
                self._normalized_averages[name].append(normalized_repeat_avg)
                self._normalized_standard_errors[name].append(normalized_repeat_ste)
            self._averages[name] = np.array(self._averages[name])
            self._standard_errors[name] = np.array(self._standard_errors[name])
            self._normalized_averages[name] = np.array(self._normalized_averages[name])
            self._normalized_standard_errors[name] = np.array(self._normalized_standard_errors[name])

    def averages(self, group_name: str, mode: Literal["all", "probe_repeats"] = "all"):
        data = self._averages[group_name]
        if mode == "all":
            return np.average(data, axis=(0, 1))
        elif mode == "probe_repeats":
            return np.average(data, axis=0)
        else:
            raise ValueError(f"Mode {mode} is not defined.")

    def errors(self, group_name: str, mode: Literal["all", "probe_repeats"] = "all"):
        data = self._averages[group_name]
        if mode == "all":
            if data.shape[0] * data.shape[1] > 1:
                return np.std(data, axis=(0, 1)) / np.sqrt(data.shape[0] * data.shape[1] - 1)
            else:
                print("No repeats found. Using the dataset standard error.")
                return self._standard_errors[group_name][0][0]
        elif mode == "probe_repeats":
            if data.shape[0] > 1:
                return np.std(data, axis=0) / np.sqrt(data.shape[0] - 1)
            else:
                print("No repeats found. Using the dataset standard error.")
                return self._standard_errors[group_name][0]
        else:
            raise ValueError(f"Mode {mode} is not defined.")

    def normalized_averages(self, group_name: str, mode: Literal["all", "probe_repeats"] = "all"):
        data = self._normalized_averages[group_name]
        if mode == "all":
            return np.average(data, axis=(0, 1))
        elif mode == "probe_repeats":
            return np.average(data, axis=0)
        else:
            raise ValueError(f"Mode {mode} is not defined.")

    def normalized_errors(self, group_name: str, mode: Literal["all", "probe_repeats"] = "all"):
        data = self._normalized_averages[group_name]
        if mode == "all":
            if data.shape[0] * data.shape[1] > 1:
                return np.std(data, axis=(0, 1)) / np.sqrt(data.shape[0] * data.shape[1] - 1)
            else:
                print("No repeats found. Using the dataset standard error.")
                return self._normalized_standard_errors[group_name][0][0]
        elif mode == "probe_repeats":
            if data.shape[0] > 1:
                return np.std(data, axis=0) / np.sqrt(data.shape[0] - 1)
            else:
                print("No repeats found. Using the dataset standard error.")
                return self._normalized_standard_errors[group_name][0]
        else:
            raise ValueError(f"Mode {mode} is not defined.")
