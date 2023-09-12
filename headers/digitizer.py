# Interface to Agilent L4532A digitizer
# Amar Vutha
# changelog: v2: 2017-10-22
#               1) simplified code, fixed so that two channels can be simultaneously sampled
#               2) removed support for records and "num_traces"
#               3) data format can be specified at initialization
#               4) fetch:waveform:adc needed if data format is adc16, whereas fetch:waveform:voltage needed if data format is float32

# Scott Smale 2022-03-06
# Rewritten for Ethernet connection.
# I also cleaned up some functions and added documentation.
# The usb capability is implemented by subclassing DigitizerEth and
#  redefining the low level functions. I have not tested it beyond seeing that
#  it creates an instance and connects without errors.
# Note: the definition of a Record (which is what we read as data) is on
#  page 103 in the manual.
# 2022-03-09
# Added the low level class DigitizerEthSock that takes Shira's code for
# reading and writing using low level sockets.
# Mingyu Fan 2023-09-09
# Refactors the code so it is clearer. Removes hacks and special cases in the code.

from typing import List, Literal, Tuple, Union

import numpy as np
import pyvisa


class Digitizer:
    def __init__(self, verbose: bool = False):
        self._verbose = verbose
        self._open_connection()
        self.clear_errors(verbose)
        self.set_clock_source_internal()
        self.set_byteorder()
        self.set_integer_data_format()
        self.set_float_data_format()

    # communication functions
    def _open_connection(self):
        raise NotImplementedError()

    def _close_connection(self):
        raise NotImplementedError()

    def _write(self, command: str):
        raise NotImplementedError()

    def _read(self) -> str:
        raise NotImplementedError()

    def _query(self, command: str) -> str:
        raise NotImplementedError()

    def _query_binary_values_adc16(self, command: str) -> np.ndarray:
        """Query for a response that will give int16 binary values.

        Returns a numpy array with int16 elements.
        """
        raise NotImplementedError()

    def _query_binary_values_float32(self, command: str) -> np.ndarray:
        """Query for a response that will give float32 binary values.

        Returns a numpy array with float32 elements.
        """
        raise NotImplementedError()

    # helper functions
    def _channel_list_to_str(self, channels: List[int]) -> str:
        result = "(@"
        for channel in channels:
            result += f"{channel},"
        return result[:-1] + ")"

    def _adc16_to_volt(self, data: np.ndarray, voltage_range: float):
        err_indices = data == -32768
        voltage = data.astype(float) / 32767 * voltage_range
        voltage[err_indices] = np.nan
        return voltage

    def clear_errors(self, verbose: bool = False):
        msg = ""
        while '+0,"No error"' not in msg:
            msg = self.get_error()
            if verbose:
                print(msg)

    # device method wrappers
    def get_name(self) -> str:
        return self._query("*IDN?")

    def get_error(self) -> str:
        return self._query("SYSTEM:ERROR?")

    def reset(self):
        self._write("*RST")

    def self_test(self):
        if int(self._query("*TST?")) != 0:
            raise Exception("Self-test failed.")

    def autozero(self, channels: List[int]):
        if (
            int(self._query(f"CAL:ZERO:AUTO? {self._channel_list_to_str(channels)}"))
            != 0
        ):
            raise Exception("Auto-zero calibration failed.")

    def configure_acquisition(
        self,
        sample_rate: Literal[
            1000,
            2000,
            5000,
            10000,
            20000,
            50000,
            100000,
            200000,
            500000,
            1000000,
            2000000,
            5000000,
            10000000,
            20000000,
        ],
        samples_per_record: int,
        pre_trig_samples_per_record: int = 0,
        num_records: int = 1,
        trigger_holdoff: int = 0,
        trigger_delay: int = 0,
    ):
        self._write(
            f"CONF:ACQ {sample_rate},{samples_per_record},{pre_trig_samples_per_record},{num_records},{trigger_holdoff},{trigger_delay}"
        )

    def get_sample_rate(self) -> int:
        return int(self._query("CONF:ACQ:SRAT?"))

    def get_samples_per_record(self) -> int:
        return int(self._query("CONF:ACQ:SCO?"))

    def get_pre_trig_samples_per_record(self) -> int:
        return int(self._query("CONF:ACQ:SPR?"))

    def configure_channels(
        self,
        channels: List[int],
        voltage_range: float,
        coupling: Literal["DC", "AC"] = "DC",
        filter: Literal["LP_200_KHZ", "LP_2_MHZ", "LP_20_MHZ"] = "LP_20_MHZ",
    ):
        self._write(
            f"CONF:CHAN {self._channel_list_to_str(channels)},{voltage_range},{coupling},{filter}"
        )

    def get_channel_range(self, channel: int) -> float:
        return float(self._query(f"CONF:CHAN:RANG? (@{channel})"))

    def set_trigger_source_external(self, use_positive_slope: bool = True):
        self._write("CONF:TRIG:SOUR EXT")
        if use_positive_slope:
            self._write("CONF:EXT POS")
        else:
            self._write("CONF:EXT NEG")

    def set_trigger_source_immediate(self):
        self._write("CONF:TRIG:SOUR IMM")

    def set_trigger_source_edge(
        self, channel: int, level: float, use_positive_slope: bool = True
    ):
        self._write("CONF:TRIG:SOUR CHAN")
        if use_positive_slope:
            self._write(f"CONF:TRIG:SOUR:CHAN:EDGE {channel},{level},POS")
        else:
            self._write(f"CONF:TRIG:SOUR:CHAN:EDGE {channel},{level},NEG")

    def set_byteorder(self, use_little_endian: bool = True):
        if use_little_endian:
            self._write("FORM:BORD SWAP")
        else:
            self._write("FORM:BORD NORM")

    def set_integer_data_format(self, format: Literal["adc16", "int_ascii"] = "adc16"):
        if format == "adc16":
            self._write("FORM:INT INT")
        elif format == "int_ascii":
            self._write("FORM:INT ASC")
        else:
            raise ValueError(f"Format {format} is not valid.")

    def set_float_data_format(
        self, format: Literal["real32", "real64", "real_ascii"] = "real32"
    ):
        if format == "real32":
            self._write("FORM:REAL REAL,32")
        elif format == "real64":
            self._write("FORM:REAL REAL,64")
        elif format == "real_ascii":
            self._write("FORM:REAL ASC,7")
        else:
            raise ValueError(f"Format {format} is not valid.")

    def set_clock_source_internal(self, use_internal: bool = True):
        if use_internal:
            self._write("CONF:ROSC INT")
        else:
            self._write("CONF:ROSC EXT")

    def get_clock_source_internal(self) -> int:
        return "INT" in self._query("CONF:ROSC?")

    def set_arm(
        self,
        source: Literal["immediate", "external", "software", "timer"] = "immediate",
        triggers_per_arm: int = 1,
    ):
        if source == "immediate":
            self._write(f"CONF:ARM:SOUR IMM,{triggers_per_arm}")
        elif source == "external":
            self._write(f"CONF:ARM:SOUR EXT,{triggers_per_arm}")
        elif source == "software":
            self._write(f"CONF:ARM:SOUR SOFT,{triggers_per_arm}")
        elif source == "timer":
            self._write(f"CONF:ARM:SOUR TIM,{triggers_per_arm}")
        else:
            raise ValueError(f"Arm source {source} is not valid.")

    def initiate_data_acquisition(self):
        self._write("INIT")

    def abort_data_acquisition(self):
        self._write("ABOR")

    def send_immediate_trigger(self):
        self._write("TRIG:IMM")

    def get_waveforms(
        self, channels: List[int], records: Union[int, Tuple[int, int]] = 1
    ) -> np.ndarray:
        """Gets the waveform data.

        Args:
            channels: list of ints, channels to read the data from.
            records: int or 2-tuple of ints. If int, it is the record number to read from.
                If a tuple, it specifies the start and end record number range to read from.
                The first record is number 1.
        """
        samples = self.get_samples_per_record()
        pre_trigger_samples = self.get_pre_trig_samples_per_record()
        post_trigger_samples = samples - pre_trigger_samples
        command = f"FETC:WAV:ADC? {self._channel_list_to_str(channels)}"
        command += f",{pre_trigger_samples},{post_trigger_samples}"
        if isinstance(records, tuple):
            command += f",(@{records[0]}:{records[1]})"
            record_numbers = list(range(*records)) + [records[1]]
        elif isinstance(records, int):
            command += f",(@{records})"
            record_numbers = [records]
        else:
            raise ValueError(f"Records {records} is not a valid value.")
        data = self._query_binary_values_adc16(command)
        data = np.reshape(data, (len(record_numbers), samples, len(channels)))
        data = np.transpose(data, axes=(2, 0, 1)).astype(float)
        channels = sorted(channels)
        for kk in range(len(channels)):
            voltage_range = self.get_channel_range(channels[kk])
            data[kk] = self._adc16_to_volt(data[kk], voltage_range)
        return data


class DigitizerVisa(Digitizer):
    def __init__(self, ip_address: str, verbose: bool = False):
        self._ip_address = ip_address
        super().__init__(verbose)

    def _open_connection(self):
        rm = pyvisa.ResourceManager()
        addr_string = f"TCPIP::{self._ip_address}::INSTR"
        if self._verbose:
            print(f"Opening connection to {addr_string}")
        self.instr: pyvisa.resources.TCPIPInstrument = rm.open_resource(addr_string)
        if self._verbose:
            print("Connection opened.")

    def _close_connection(self):
        self.instr.close()

    def _write(self, command: str):
        self.instr.write(command)

    def _read(self) -> str:
        return self.instr.read()

    def _query(self, command: str):
        return self.instr.query(command).strip()

    def _query_binary_values_adc16(self, command: str) -> np.ndarray:
        return self.instr.query_binary_values(
            command, datatype="h", container=np.array, chunk_size=2000*1024
        )

    def _query_binary_values_float32(self, command: str) -> np.ndarray:
        return self.instr.query_binary_values(
            command, datatype="f", container=np.array, chunk_size=2000*1024
        )
