"""PCIE Digitizer Header file

Updated 12/18/23 by Mingyu Fan
  - Digitizer can take many repetitions of data without crashing.
  - Allows individual control of the input voltage ranges of channels.
"""
import sys
from builtins import int
import platform
import sys
import time
from typing import Literal, Optional
import numpy as np

import onix.headers.pcie_digitizer.GageSupport as gs
import onix.headers.pcie_digitizer.GageConstants as gc
import platform


os_name = platform.system()

if os_name == "Windows":
    is_64_bits = sys.maxsize > 2**32

    if is_64_bits:
        if sys.version_info >= (3, 0):
            import PyGage3_64 as PyGage
        else:
            import PyGage2_64 as PyGage
    else:
        if sys.version_info > (3, 0):
            import PyGage3_32 as PyGage
        else:
            import PyGage2_32 as PyGage
else:
    import PyGage


VALID_SAMPLE_RATES = Literal[
    100000000,
    65000000,
    50000000,
    40000000,
    25000000,
    20000000,
    10000000,
    5000000,
    2000000,
    1000000
]
VALID_CHAN_FULL_RANGES_MV = [200, 400, 1000, 2000, 4000, 10000]

class Digitizer:
    """Header for the GaGe CSE8327 Octave Express Digitizer."""

    def __init__(self):
        self._handle = self.initialize()
        self._system_info = self.get_system_info()

    def _raise_error(self, function_called: str, error_code: int, cleanup: bool = True):
        error_string = PyGage.GetErrorString(error_code)

        (function_called, "failed with error: ", error_string, "\n")
        if cleanup:
            PyGage.FreeSystem(self._handle)
        raise SystemExit

    def initialize(self) -> int:
        status = PyGage.Initialize()
        if status < 0:
            self._raise_error("Initialize", status, cleanup=False)
        handle = PyGage.GetSystem(0, 0, 0, 0)
        if handle < 0:
            self._raise_error("GetSystem", status, cleanup=False)
        return handle

    def get_system_info(self) -> dict:
        """Get board information that cannot be changed."""
        system_info = PyGage.GetSystemInfo(self._handle)
        if not isinstance(system_info, dict):
            self._raise_error("GetSystemInfo", system_info)
        return system_info

    def get_acquisition_config(self) -> dict:
        return PyGage.GetAcquisitionConfig(self._handle)

    def set_acquisition_config(
        self,
        num_channels: Literal[1, 2],
        sample_rate: VALID_SAMPLE_RATES,
        segment_size: int,
        segment_count: int = 1,
        trigger_holdoff: int = 0,
        trigger_timeout: Optional[int] = None,
    ):
        default_acq_config = {
            "Mode": "single",
            "SampleRate": 100000000,
            "Depth": 8160,
            "SegmentSize": 8160,
            "SegmentCount": 1,
            "TriggerHoldoff": 0,
            "TriggerDelay": 0,
            "TriggerTimeout": -1,
            "ExtClk": 0,
        }

        self._overflow = (16 - segment_size % 16) % 16
        self._segment_size = segment_size + self._overflow
        acq_config = default_acq_config.copy()
        acq_config["Mode"] = num_channels
        acq_config["SampleRate"] = int(sample_rate)
        acq_config["Depth"] = int(self._segment_size)
        acq_config["SegmentSize"] = int(self._segment_size)
        acq_config["SegmentCount"] = int(segment_count)
        acq_config["TriggerHoldoff"] = int(trigger_holdoff)
        if trigger_timeout is None:
            trigger_timeout = -1
        acq_config["TriggerTimeout"] = int(trigger_timeout)
        status = PyGage.SetAcquisitionConfig(self._handle, acq_config)
        if status < 0:
            self._raise_error("SetAcquisitionConfig", status)

    def get_channel_config(self, channel: int) -> dict:
        return PyGage.GetChannelConfig(self._handle, channel)

    def set_channel_config(
        self,
        channel: Literal[1, 2],
        range: float,
        ac_coupled: bool = False,
        high_impedance: bool = False,
        use_filter: bool = True,
    ):
        default_chan_config = {
            "InputRange": 2000,
            "Coupling": gc.CS_COUPLING_DC,
            "Impedance": 50,
            "DcOffset": 0,
            "Filter": 1,
        }

        acq_config = self.get_acquisition_config()
        channel_increment = gs.CalculateChannelIndexIncrement(
            acq_config["Mode"],
            self._system_info["ChannelCount"],
            self._system_info["BoardCount"],
        )  # channel increment when multiple boards are installed.
        channel = 1 + (channel - 1) * channel_increment

        chan_config = default_chan_config.copy()
        full_range_mV = int(range * 2000)
        if full_range_mV not in VALID_CHAN_FULL_RANGES_MV:
            raise ValueError(f"Channel {channel} range of {range} V is not valid.")
        chan_config["InputRange"] = full_range_mV
        if ac_coupled:
            chan_config["Coupling"] = gc.CS_COUPLING_AC
        else:
            chan_config["Coupling"] = gc.CS_COUPLING_DC
        if high_impedance:
            chan_config["Impedance"] = 1000000
        else:
            chan_config["Impedance"] = 50
        if use_filter:
            chan_config["Filter"] = 1
        else:
            chan_config["Filter"] = 0

        status = PyGage.SetChannelConfig(self._handle, channel, chan_config)
        if status < 0:
            self._raise_error("SetChannelConfig", status)

    def get_trigger_config(self, trigger_channel: int = 1) -> dict:
        return PyGage.GetTriggerConfig(self._handle, trigger_channel)

    def set_trigger_source_software(self):  # interop with acquisition parameters.
        default_trigger_config = {
            "Condition": gc.CS_TRIG_COND_POS_SLOPE,
            "Level": 30,
            "Source": gc.CS_TRIG_SOURCE_EXT,
            "ExtRange": 5000,
            "ExtImpedance": 50,
        }
        trigger_config = default_trigger_config.copy()
        trigger_config["Source"] = 0
        status = PyGage.SetTriggerConfig(self._handle, 1, trigger_config)
        if status < 0:
            self._raise_error("SetTriggerConfig", status)

        acq_config = self.get_acquisition_config()
        if acq_config["TriggerTimeout"] < 0:
            acq_config["TriggerTimeout"] = 0

        self.set_acquisition_config(
            acq_config["Mode"],
            acq_config["SampleRate"],
            acq_config["SegmentSize"] - self._overflow,
            acq_config["SegmentCount"],
            acq_config["TriggerHoldoff"],
            acq_config["TriggerTimeout"],
        )

    def set_trigger_source_edge(
        self,
        range: float = 5.0,
        level: float = 1.2,
        positive_slope: bool = True,
        ac_coupled: bool = False,
        high_impedance: bool = False,
    ):
        default_trigger_config = {
            "Condition": gc.CS_TRIG_COND_POS_SLOPE,
            "Level": 30,
            "Source": gc.CS_TRIG_SOURCE_EXT,
            "ExtRange": 10000,
            "ExtImpedance": 50,
        }
        trigger_config = default_trigger_config.copy()
        trigger_config["Source"] = gc.CS_TRIG_SOURCE_EXT
        trigger_config["ExtRange"] = int(range * 2000)
        trigger_config["Level"] = int(level / range * 100)
        if positive_slope:
            trigger_config["Condition"] = gc.CS_TRIG_COND_POS_SLOPE
        else:
            trigger_config["Condition"] = gc.CS_TRIG_COND_NEG_SLOPE
        if ac_coupled:
            trigger_config["ExtCoupling"] = gc.CS_COUPLING_AC
        else:
            trigger_config["ExtCoupling"] = gc.CS_COUPLING_DC
        if high_impedance:
            trigger_config["ExtImpedance"] = 1000000
        else:
            trigger_config["ExtImpedance"] = 50
        status = PyGage.SetTriggerConfig(self._handle, 1, trigger_config)
        if status < 0:
            self._raise_error("SetTriggerConfig", status)

    def write_configs_to_device(self):
        status = PyGage.Commit(self._handle)
        if status < 0:
            self._raise_error("Commit", status)

    def start_capture(self):
        status = PyGage.StartCapture(self._handle)
        if status < 0:
            self._raise_error("StartCapture", status)

    def wait_for_data_ready(self, timeout=None):
        t_start = time.time()
        t_end = time.time()
        status = PyGage.GetStatus(self._handle)
        while status != gc.ACQ_STATUS_READY and (timeout is None or timeout > t_end - t_start):
            time.sleep(0.001)
            status = PyGage.GetStatus(self._handle)
            t_end = time.time()
        if status != gc.ACQ_STATUS_READY:
            raise RuntimeError(f"Digitizer timeout with error {status}.")

    def get_data(self):
        acq_config = self.get_acquisition_config()
        channel_increment = gs.CalculateChannelIndexIncrement(
            acq_config["Mode"], self._system_info["ChannelCount"], self._system_info["BoardCount"]
        )

        start_address = acq_config["TriggerDelay"] + acq_config["Depth"] - acq_config["SegmentSize"]
        data_length = acq_config["TriggerDelay"] + acq_config["Depth"] - start_address

        sample_rate = acq_config["SampleRate"]
        if acq_config["ExtClk"]:
            sample_rate /= (acq_config["ExtClkSampleSkip"] * 1000)

        channel_data = []

        for channel in range(1, self._system_info["ChannelCount"] + 1, channel_increment):
            segment_data = []
            for group in range(1, acq_config["SegmentCount"] + 1):
                data = PyGage.TransferData(
                    self._handle, channel, gc.TxMODE_DEFAULT, group, start_address, data_length
                )
                if isinstance(data, int):
                    self._raise_error("TransferData", data)

                data = np.array(data[0])
                data = data[:data_length - self._overflow]

                full_range_mV = self.get_channel_config(channel)["InputRange"]
                data = data * (full_range_mV * 1e-3 / 2**16)
                segment_data.append(data)
            segment_data = np.array(segment_data)
            channel_data.append(segment_data)
        return (sample_rate, np.array(channel_data))

    def close(self):
        """Release the handle to the Digitizer."""
        PyGage.FreeSystem(self._handle)

