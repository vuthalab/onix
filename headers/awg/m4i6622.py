from typing import Literal, Optional, Union

import numpy as np

import onix.headers.awg.pyspcm as pyspcm

from onix.headers.awg.spcm_tools import pvAllocMemPageAligned
from onix.control.segments import (
    AllBoardSegments, Segment
)
from onix.control.awg_functions import AWGSinePulse
from onix.control.ttl_functions import TTLOff, TTLOn
from onix.units import Q_, ureg

CHANNEL_TYPE = Literal[0, 1, 2, 3]
MAX_SAMPLE_RATE = 625000000


class M4i6622:
    """Header for the M4i6622 arbitrary waveform generator.

    It has a sine output mode and a sequence mode.
    The sine output mode allows outputting sine waves (much greater than 1 kHz frequency)
    on AWG channels, and high or low levels on TTL channels.
    The sequence mode allows running more complicated waveforms with hardware timing.

    Currently it may have a bug preventing it to switch between the two modes.
    It is probably the safest to always restart the python kernel when switching to another mode.
    TODO: Check if this bug is still present. If present, fix this bug.

    It supports a "primary" AWG controlling one or several "secondary" AWGs.
    The TTL0 of the primary AWG is used to trigger the rest of the secondary AWGs at the start
    of the sequence in the sequence mode.
    The channels of the secondary AWGs are indexed as incrementing integers after the channel
    numbers of the primary AWG. For example, the secondary AWG #1 have AWG channels 4 - 7 and
    TTL channels 3 to 5.

    All AWGs should be on the same clock source to ensure identical frequency and timing.
    
    A typical use case is to have the primary AWG outputting state preparation and detection
    pulses (which does not need to be changed), and have a secondary AWG outputting the
    spectroscopy pulses which may sweep in frequency or phase. As the secondary AWG only needs
    to know the spectroscopy pulses, it may have enough memory to store the pulses with all
    different frequencies or phases in the memory, so the sweep can happen without reprogramming
    the AWG board.

    The TTL channel information cuts the amplitude accuracy of channels 0 to 2 of each board
    from 16 bits to 15 bits. The highest sampling rate, 625 Mps is always used.

    TODO: support using only 1 or 2 channels of a card. This will allow loading longer sequences.
    First needs to support having more than one TTL channel information stored on a AWG channel
    (the channel amplitude resolution will drop to 14 bits or 13 bits).

    Example for outputting sine waves:
        m4i = M4i6622(...)
        m4i.set_sine_output(channel, frequency, amplitude)  # sets a channel to output a sine wave.
        m4i.set_ttl_output(channel, state)  # sets a TTL channel to be on or off.
        m4i.start_sine_outputs()  # starts the output.
        m4i.stop_sine_outputs()  # stops the output.
        # The set_sine_output and set_ttl_output functions can be called at any time.
        # If called when the sine outputs are on, the output will change within a few ms.

    Example for running a pulse sequence:
        m4i = M4i6622(...)
        m4i.setup_segments(...)  # see onix.control.segments.AllBoardSegments class.

        # the code below can be run without setting up the sequence again.
        for kk in range(repeats):
            m4i.start_sequence()
            m4i.wait_for_sequence_complete()
        m4i.stop_sequence()
    """

    def __init__(
        self,
        addresses: Union[list[str], str] = ["/dev/spcm0", "/dev/spcm1"],
        external_clock_frequency: Optional[int] = 10000000,
    ):
        if not isinstance(addresses, list):
            addresses = [addresses]

        self._hcards = []
        for address in addresses:
            hcard = pyspcm.spcm_hOpen(
                pyspcm.create_string_buffer(address.encode("ascii"))
            )
            if hcard is None:
                raise Exception(f"No card is found at {address}.")
            self._hcards.append(hcard)
        self._number_of_cards = len(self._hcards)
        self._aligned_buffer = [None for kk in self._hcards]
        self._segment_name_maps = {}

        for hcard in self._hcards:
            self._reset(hcard)
        self._bytes_per_sample = self._get_bytes_per_sample(self._hcards[0])

        if external_clock_frequency is not None:
            for hcard in self._hcards:
                self._set_clock_mode(hcard, "external_reference")
                self._set_external_clock_frequency(hcard, external_clock_frequency)
        else:
            for hcard in self._hcards:
                self._set_clock_mode(hcard, "internal_pll")

        for hcard in self._hcards:
            self._set_sample_rate(hcard)
        self._sample_rate = self._get_sample_rate(self._hcards[0])

        self._set_trigger_or_mask(self._hcards[0], pyspcm.SPC_TMASK_SOFTWARE)
        self._set_trigger_and_mask(self._hcards[0], pyspcm.SPC_TMASK_NONE)
        for hcard in self._hcards[1:]:
            self._set_trigger_or_mask(hcard, pyspcm.SPC_TMASK_EXT0)
            self._set_trigger_and_mask(hcard, pyspcm.SPC_TMASK_NONE)
            self._set_ext0_trigger_impedance(hcard, is_50_ohm = True)
            self._set_ext0_trigger_level(hcard, level = 750)
            self._set_ext0_trigger_rising_edge(hcard)

        self._awg_channels = list(range(4 * self._number_of_cards))
        self._ttl_channels = list(range(3 * self._number_of_cards))
        for hcard in self._hcards:
            self._select_channels(hcard, [0,1,2,3])

        for awg_channel in [0, 1, 2, 3]:
            for hcard in self._hcards:
                self._enable_channel(hcard, awg_channel)
                self._set_channel_amplitude(hcard, awg_channel)
                self._set_channel_filter(hcard, awg_channel)

        # Maps of TTL channels mixing with AWG channels
        self._ttl_awg_map = {0: 0, 1: 1, 2: 2}

        for hcard in self._hcards:
            for ttl_channel in [0,1,2]:
                mode = pyspcm.SPCM_XMODE_DIGOUT

                mode = mode | getattr(
                    pyspcm, f"SPCM_XMODE_DIGOUTSRC_CH{self._ttl_awg_map[ttl_channel]}"
                )

                mode = mode | pyspcm.SPCM_XMODE_DIGOUTSRC_BIT15
                self._set_multi_purpose_io_mode(hcard, ttl_channel, mode)

        # implements the sine segments.
        self._next_sine_segment = 0
        self._awg_parameters = {}
        for channel in self._awg_channels:
            self._awg_parameters[channel] = {"frequency": 0 * ureg.Hz, "amplitude": 0}
        self._ttl_parameters = []
        for channel in self._ttl_channels:
            self._ttl_parameters.append(False)
        self._sine_segment_duration = 4 * ureg.ms
        self._sine_segments = {
            "__sine_0": Segment("__sine_0", duration=self._sine_segment_duration),
            "__sine_1": Segment("__sine_1", duration=self._sine_segment_duration),
        }
        self._sine_segment_running = False
        self._set_sine_segment()
        default_segments = AllBoardSegments(self._number_of_cards)
        default_segments.insert_segments(self._sine_segments)
        default_segments.setup_sequence([("__sine_0", 1), ("__sine_1", 1)])
        self.setup_segments(default_segments)

    # device methods
    def _get_bytes_per_sample(self, hcard) -> int:
        value = pyspcm.int32(0)
        ret = pyspcm.spcm_dwGetParam_i32(
            hcard, pyspcm.SPC_MIINST_BYTESPERSAMPLE, pyspcm.byref(value)
        )
        if ret != pyspcm.ERR_OK:
            raise Exception(f"Get bytes per sample failed with code {ret}.")
        return value.value

    def _select_channels(self, hcard, channels: list[CHANNEL_TYPE]):
        if len(channels) == 3:
            raise ValueError("Cannot enable 3 channels. Enable 4 channels instead.")
        value = 0
        for channel in channels:
            value = value | getattr(pyspcm, f"CHANNEL{channel}")
        ret = pyspcm.spcm_dwSetParam_i64(hcard, pyspcm.SPC_CHENABLE, value)
        if ret != pyspcm.ERR_OK:
            raise Exception(f"Select channels failed with code {ret}.")

    def _enable_channel(self, hcard, channel: CHANNEL_TYPE, enabled: bool = True):
        if enabled:
            value = pyspcm.int64(1)
        else:
            value = pyspcm.int64(0)
        ret = pyspcm.spcm_dwSetParam_i64(
            hcard, getattr(pyspcm, f"SPC_ENABLEOUT{channel}"), value
        )
        if ret != pyspcm.ERR_OK:
            raise Exception(f"Enable channel failed with code {ret}.")

    def _set_channel_amplitude(self, hcard, channel: CHANNEL_TYPE, amplitude_mV: int = 2500):
        ret = pyspcm.spcm_dwSetParam_i32(
            hcard,
            getattr(pyspcm, f"SPC_AMP{channel}"),
            pyspcm.int32(amplitude_mV),
        )
        if ret != pyspcm.ERR_OK:
            raise Exception(f"Set channel amplitude failed with code {ret}.")

    def _set_channel_filter(self, hcard, channel: CHANNEL_TYPE, filter: int = 0):
        ret = pyspcm.spcm_dwSetParam_i32(
            hcard, getattr(pyspcm, f"SPC_FILTER{channel}"), pyspcm.int32(filter)
        )
        if ret != pyspcm.ERR_OK:
            raise Exception(f"Set channel filter failed with code {ret}.")

    def _set_mode(
        self,
        hcard,
        mode: Literal[
            "single",
            "multiple",
            "single_restart",
            "sequence",
        ],
    ):
        """See replay modes in the manual. Not all modes are implemented here."""
        if mode == "single":
            value = pyspcm.SPC_REP_STD_SINGLE
        elif mode == "multiple":
            value = pyspcm.SPC_REP_STD_MULTI
        elif mode == "single_restart":
            value = pyspcm.SPC_REP_STD_SINGLERESTART
        elif mode == "sequence":
            value = pyspcm.SPC_REP_STD_SEQUENCE
        else:
            raise ValueError(f"The replay mode {mode} is invalid or not implemented.")
        ret = pyspcm.spcm_dwSetParam_i32(hcard, pyspcm.SPC_CARDMODE, value)
        if ret != pyspcm.ERR_OK:
            raise Exception(f"Set mode failed with code {ret}.")

    def _reset(self, hcard):
        """Resets the card."""
        ret = pyspcm.spcm_dwSetParam_i32(
            hcard, pyspcm.SPC_M2CMD, pyspcm.M2CMD_CARD_RESET
        )
        if ret != pyspcm.ERR_OK:
            raise Exception(f"Reset failed with code {ret}.")

    def _write_setup(self, hcard):
        """Writes the setup without starting the card."""
        ret = pyspcm.spcm_dwSetParam_i32(
            hcard, pyspcm.SPC_M2CMD, pyspcm.M2CMD_CARD_WRITESETUP
        )
        if ret != pyspcm.ERR_OK:
            raise Exception(f"Write setup failed with code {ret}.")

    def _start(self, hcard):
        """Writes the setup and starts the card."""
        ret = pyspcm.spcm_dwSetParam_i32(
            hcard, pyspcm.SPC_M2CMD, pyspcm.M2CMD_CARD_START
        )
        if ret != pyspcm.ERR_OK:
            raise Exception(f"Start card failed with code {ret}.")

    def _enable_triggers(self, hcard):
        """Enables detecting triggers."""
        ret = pyspcm.spcm_dwSetParam_i32(
            hcard, pyspcm.SPC_M2CMD, pyspcm.M2CMD_CARD_ENABLETRIGGER
        )
        if ret != pyspcm.ERR_OK:
            raise Exception(f"Enable triggers failed with code {ret}.")

    def _force_trigger(self, hcard):
        """Sends a software trigger."""
        ret = pyspcm.spcm_dwSetParam_i32(
            hcard, pyspcm.SPC_M2CMD, pyspcm.M2CMD_CARD_FORCETRIGGER
        )
        if ret != pyspcm.ERR_OK:
            raise Exception(f"Force trigger failed with code {ret}.")

    def _disable_triggers(self, hcard):
        """Disables detecting triggers."""
        ret = pyspcm.spcm_dwSetParam_i32(
            hcard, pyspcm.SPC_M2CMD, pyspcm.M2CMD_CARD_DISABLETRIGGER
        )
        if ret != pyspcm.ERR_OK:
            raise Exception(f"Disable triggers failed with code {ret}.")

    def _stop(self, hcard):
        """Stops the current run of the card."""
        ret = pyspcm.spcm_dwSetParam_i32(
            hcard, pyspcm.SPC_M2CMD, pyspcm.M2CMD_CARD_STOP
        )
        if ret != pyspcm.ERR_OK:
            raise Exception(f"Stop card failed with code {ret}.")

    def _wait_for_trigger(self, hcard):
        """Waits until the first trigger event has been detected by the card."""
        ret = pyspcm.spcm_dwSetParam_i32(
            hcard, pyspcm.SPC_M2CMD, pyspcm.M2CMD_CARD_WAITTRIGGER
        )
        if ret != pyspcm.ERR_OK:
            raise Exception(f"Wait for trigger failed with code {ret}.")

    def _wait_for_complete(self, hcard):
        """Waits until the card has completed the current run."""
        ret = pyspcm.spcm_dwSetParam_i32(
            hcard, pyspcm.SPC_M2CMD, pyspcm.M2CMD_CARD_WAITREADY
        )
        if ret != pyspcm.ERR_OK:
            raise Exception(f"Wait for complete failed with code {ret}.")

    def _define_transfer_buffer(
        self,
        hcard,
        index: int,
        data: np.ndarray,
        transfer_offset: int = 0,
    ) -> int:
        self._aligned_buffer[index] = pvAllocMemPageAligned(len(data) * self._bytes_per_sample)
        # this variable must maintain a reference after exit.
        data = data.astype(np.int16)
        pyspcm.memmove(self._aligned_buffer[index], data.ctypes.data, 2 * len(data))
        ret = pyspcm.spcm_dwDefTransfer_i64(
            hcard,
            pyspcm.SPCM_BUF_DATA,
            pyspcm.SPCM_DIR_PCTOCARD,
            pyspcm.uint32(0),
            self._aligned_buffer[index],
            pyspcm.uint64(transfer_offset),
            pyspcm.uint64(len(self._aligned_buffer[index])),
        )
        if ret != pyspcm.ERR_OK:
            raise Exception(f"Define transfer buffer failed with code {ret}.")
        return len(self._aligned_buffer[index])

    def _get_data_ready_to_transfer(self, hcard) -> int:
        value = pyspcm.int32(0)
        ret = pyspcm.spcm_dwGetParam_i32(
            hcard, pyspcm.SPC_DATA_AVAIL_USER_LEN, pyspcm.byref(value)
        )
        if ret != pyspcm.ERR_OK:
            raise Exception(f"Get data ready to transfer failed with code {ret}.")
        return value.value

    def _set_data_ready_to_transfer(self, hcard, data_bytes: int):
        ret = pyspcm.spcm_dwSetParam_i32(
            hcard, pyspcm.SPC_DATA_AVAIL_CARD_LEN, pyspcm.int32(data_bytes)
        )
        if ret != pyspcm.ERR_OK:
            raise Exception(f"Set data ready to transfer failed with code {ret}.")

    def _start_dma_transfer(self, hcard, wait: bool = False):
        if wait:
            value = pyspcm.M2CMD_DATA_STARTDMA | pyspcm.M2CMD_DATA_WAITDMA
        else:
            value = pyspcm.M2CMD_DATA_STARTDMA
        ret = pyspcm.spcm_dwSetParam_i32(hcard, pyspcm.SPC_M2CMD, value)
        if ret != pyspcm.ERR_OK:
            raise Exception(f"Start DMA transfer failed with code {ret}.")

    def _wait_dma_transfer(self, hcard):
        ret = pyspcm.spcm_dwSetParam_i32(
            hcard, pyspcm.SPC_M2CMD, pyspcm.M2CMD_DATA_WAITDMA
        )
        if ret != pyspcm.ERR_OK:
            raise Exception(f"Wait DMA transfer failed with code {ret}.")

    def _stop_dma_transfer(self, hcard):
        ret = pyspcm.spcm_dwSetParam_i32(
            hcard, pyspcm.SPC_M2CMD, pyspcm.M2CMD_DATA_STOPDMA
        )
        if ret != pyspcm.ERR_OK:
            raise Exception(f"Stop DMA transfer failed with code {ret}.")

    def _set_memory_size(self, hcard, samples_per_channel: int):
        ret = pyspcm.spcm_dwSetParam_i64(
            hcard, pyspcm.SPC_MEMSIZE, pyspcm.int64(samples_per_channel)
        )
        if ret != pyspcm.ERR_OK:
            raise Exception(f"Set memory size failed with code {ret}.")

    def _set_segment_size(self, hcard, samples_per_segment: int):
        ret = pyspcm.spcm_dwSetParam_i64(
            hcard, pyspcm.SPC_SEGMENTSIZE, pyspcm.int64(samples_per_segment)
        )
        if ret != pyspcm.ERR_OK:
            raise Exception(f"Set segment size failed with code {ret}.")

    def _set_number_of_loops(self, hcard, loops: int):
        ret = pyspcm.spcm_dwSetParam_i64(
            hcard, pyspcm.SPC_LOOPS, pyspcm.int64(loops)
        )
        if ret != pyspcm.ERR_OK:
            raise Exception(f"Set number of loops failed with code {ret}.")

    def _set_clock_mode(
        self,
        hcard,
        clock_mode: Literal[
            "internal_pll", "quartz2", "external_reference", "pxi_reference"
        ],
    ):
        if clock_mode == "internal_pll":
            value = pyspcm.SPC_CM_INTPLL
        elif clock_mode == "quartz2":
            value = pyspcm.SPC_CM_QUARTZ2
        elif clock_mode == "external_reference":
            value = pyspcm.SPC_CM_EXTREFCLOCK
        elif clock_mode == "pxi_reference":
            value = pyspcm.SPC_CM_PXIREFCLOCK
        else:
            raise ValueError(f"Clock mode {clock_mode} is not valid.")
        ret = pyspcm.spcm_dwSetParam_i32(hcard, pyspcm.SPC_CLOCKMODE, value)
        if ret != pyspcm.ERR_OK:
            raise Exception(f"Set clock mode failed with code {ret}.")

    def _get_sample_rate(self, hcard) -> int:
        value = pyspcm.int64(0)
        ret = pyspcm.spcm_dwGetParam_i64(
            hcard, pyspcm.SPC_SAMPLERATE, pyspcm.byref(value)
        )
        if ret != pyspcm.ERR_OK:
            raise Exception(f"Get sample rate failed with code {ret}.")
        return value.value

    def _set_sample_rate(self, hcard, sample_rate: int = MAX_SAMPLE_RATE):
        ret = pyspcm.spcm_dwSetParam_i64(
            hcard, pyspcm.SPC_SAMPLERATE, pyspcm.int64(sample_rate)
        )
        if ret != pyspcm.ERR_OK:
            raise Exception(f"Set sample rate failed with code {ret}.")

    def _set_external_clock_frequency(self, hcard, clock_frequency: int):
        ret = pyspcm.spcm_dwSetParam_i32(
            hcard, pyspcm.SPC_REFERENCECLOCK, pyspcm.int32(clock_frequency)
        )
        if ret != pyspcm.ERR_OK:
            raise Exception(f"Set external clock frequency failed with code {ret}.")

    def _set_trigger_or_mask(self, hcard, trigger_mask: int):
        ret = pyspcm.spcm_dwSetParam_i32(
            hcard, pyspcm.SPC_TRIG_ORMASK, pyspcm.int32(trigger_mask)
        )
        if ret != pyspcm.ERR_OK:
            raise Exception(f"Set trigger OR mask failed with code {ret}.")

    def _set_trigger_and_mask(self, hcard, trigger_mask: int):
        ret = pyspcm.spcm_dwSetParam_i32(
            hcard, pyspcm.SPC_TRIG_ANDMASK, pyspcm.int32(trigger_mask)
        )
        if ret != pyspcm.ERR_OK:
            raise Exception(f"Set trigger AND mask failed with code {ret}.")

    def _set_ext0_trigger_impedance(self, hcard, is_50_ohm = True):
        """Set the trigger impedance"""
        if is_50_ohm:
            ret = pyspcm.spcm_dwSetParam_i32(
                hcard, pyspcm.SPC_TRIG_TERM, pyspcm.int32(1)
            )
        else:
            ret = pyspcm.spcm_dwSetParam_i32(
                hcard, pyspcm.SPC_TRIG_TERM, pyspcm.int32(0)
            )
        if ret != pyspcm.ERR_OK:
            raise Exception(f"Set trigger impedance failed with code {ret}.")

    def _set_ext0_trigger_level(self, hcard, level):
        """Set the trigger level"""
        ret = pyspcm.spcm_dwSetParam_i32(
            hcard, pyspcm.SPC_TRIG_EXT0_LEVEL0, pyspcm.int32(level)
        )
        if ret != pyspcm.ERR_OK:
            raise Exception(f"Set trigger level failed with code {ret}.")

    def _set_ext0_trigger_rising_edge(self, hcard):
        """Set trigger edge to rising or falling"""
        ret = pyspcm.spcm_dwSetParam_i32(
            hcard, pyspcm.SPC_TRIG_EXT0_MODE, pyspcm.SPC_TM_POS
        )
        if ret != pyspcm.ERR_OK:
            raise Exception(f"Set trigger edge to rising failed with code {ret}.")

    def _set_ext0_trigger_falling_edge(self, hcard):
        """Set trigger edge to falling"""
        ret = pyspcm.spcm_dwSetParam_i32(
            hcard, pyspcm.SPC_TRIG_EXT0_MODE, pyspcm.SPC_TM_NEG
        )
        if ret != pyspcm.ERR_OK:
            raise Exception(f"Set trigger edge to falling failed with code {ret}.")

    def _set_ext0_trigger_level_high(self, hcard):
        """Trigger detection for high levels (signal above level 0)"""
        ret = pyspcm.spcm_dwSetParam_i32(
            hcard, pyspcm.SPC_TRIG_EXT0_MODE, pyspcm.SPC_TM_HIGH
        )
        if ret != pyspcm.ERR_OK:
            raise Exception(f"Set trigger level to high failed with code {ret}.")

    def _set_ext0_trigger_level_low(self, hcard):
        """Trigger detection for low levels (signal below level 0)"""
        ret = pyspcm.spcm_dwSetParam_i32(
            hcard, pyspcm.SPC_TRIG_EXT0_MODE, pyspcm.SPC_TM_LOW
        )
        if ret != pyspcm.ERR_OK:
            raise Exception(f"Set trigger level to low failed with code {ret}.")


    def _set_multi_purpose_io_mode(self, hcard, line_number: Literal[0, 1, 2], mode: int):
        ret = pyspcm.spcm_dwSetParam_i32(
            hcard,
            getattr(pyspcm, f"SPCM_X{line_number}_MODE"),
            pyspcm.int32(mode),
        )
        if ret != pyspcm.ERR_OK:
            raise Exception(f"Set multiple purpose io mode failed with code {ret}.")

    def _get_multi_purpose_io_output(self, hcard) -> tuple[bool, bool, bool]:
        mode = pyspcm.int32(0)
        ret = pyspcm.spcm_dwGetParam_i32(
            hcard, pyspcm.SPCM_XX_ASYNCIO, pyspcm.byref(mode)
        )
        if ret != pyspcm.ERR_OK:
            raise Exception(f"Get multi purpose io output failed with code {ret}.")
        return (mode.value & 1 != 0, mode.value & 2 != 0, mode.value & 4 != 0)

    def _set_multi_purpose_io_output(
        self, hcard, x0_state: bool, x1_state: bool, x2_state: bool
    ):
        mode = 0
        if x0_state:
            mode += 1
        if x1_state:
            mode += 2
        if x2_state:
            mode += 4
        ret = pyspcm.spcm_dwSetParam_i32(
            hcard, pyspcm.SPCM_XX_ASYNCIO, pyspcm.int32(mode)
        )
        if ret != pyspcm.ERR_OK:
            raise Exception(f"Set multi purpose io output failed with code {ret}.")

    def _set_sequence_max_segments(self, hcard, segments: int):
        ret = pyspcm.spcm_dwSetParam_i32(
            hcard, pyspcm.SPC_SEQMODE_MAXSEGMENTS, pyspcm.int32(segments)
        )
        if ret != pyspcm.ERR_OK:
            raise Exception(f"Set sequence max segments failed with code {ret}.")

    def _set_sequence_write_segment(self, hcard, segment_number: int):
        ret = pyspcm.spcm_dwSetParam_i32(
            hcard, pyspcm.SPC_SEQMODE_WRITESEGMENT, pyspcm.int32(segment_number)
        )
        if ret != pyspcm.ERR_OK:
            raise Exception(f"Set sequence write segment failed with code {ret}.")

    def _set_sequence_write_segment_size(self, hcard, segment_size: int):
        ret = pyspcm.spcm_dwSetParam_i32(
            hcard, pyspcm.SPC_SEQMODE_SEGMENTSIZE, pyspcm.int32(segment_size)
        )
        if ret != pyspcm.ERR_OK:
            raise Exception(f"Set sequence write segment size failed with code {ret}.")

    def _set_segment_step_memory(
        self,
        hcard,
        step_number: int,
        segment_number: int,
        next_step: int,
        loops: int,
        end: Literal["end_loop", "end_loop_on_trig", "end_sequence"] = "end_loop",
    ):
        """Sets the parameters for a segment step.

        For some reason that the last "end_sequence" step always don't output.
        Adding a short, empty step at the end solves the problem.
        """
        register = pyspcm.SPC_SEQMODE_STEPMEM0 + step_number
        if end == "end_loop":
            end = pyspcm.SPCSEQ_ENDLOOPALWAYS
        elif end == "end_loop_on_trig":
            end = pyspcm.SPCSEQ_ENDLOOPONTRIG
        elif end == "end_sequence":
            end = pyspcm.SPCSEQ_END
        value = (end << 32) | (loops << 32) | (next_step << 16) | segment_number
        ret = pyspcm.spcm_dwSetParam_i64(hcard, register, pyspcm.int64(value))
        if ret != pyspcm.ERR_OK:
            raise Exception(f"Set segment step memory failed with code {ret}.")

    def _get_segment_start_step(self, hcard) -> int:
        value = pyspcm.int32(0)
        ret = pyspcm.spcm_dwGetParam_i32(
            hcard, pyspcm.SPC_SEQMODE_STARTSTEP, pyspcm.byref(value)
        )
        if ret != pyspcm.ERR_OK:
            raise Exception(f"Get segment start step failed with code {ret}.")
        return value.value

    def _set_segment_start_step(self, hcard, start_step_number: int):
        ret = pyspcm.spcm_dwSetParam_i32(
            hcard, pyspcm.SPC_SEQMODE_STARTSTEP, pyspcm.int32(start_step_number)
        )
        if ret != pyspcm.ERR_OK:
            raise Exception(f"Set segment start step failed with code {ret}.")

    def _get_segment_current_step(self, hcard) -> int:
        value = pyspcm.int32(0)
        ret = pyspcm.spcm_dwSetParam_i32(
            hcard, pyspcm.SPC_SEQMODE_STATUS, pyspcm.byref(value)
        )
        if ret != pyspcm.ERR_OK:
            raise Exception(f"Get segment current step failed with code {ret}.")
        return value.value

    def _get_error_information(self, hcard) -> tuple[int, int, str]:
        error_register = pyspcm.uint32(0)
        error_code = pyspcm.int32(0)
        text = pyspcm.create_string_buffer(1000)
        ret = pyspcm.spcm_dwGetErrorInfo_i32(
            hcard, pyspcm.byref(error_register), pyspcm.byref(error_code), pyspcm.byref(text)
        )
        return (error_register.value, error_code.value, text.value.decode("utf-8"))

    # helper functions
    def _set_sine_segment(self):
        name = f"__sine_{self._next_sine_segment}"
        segment = Segment(name, duration=self._sine_segment_duration)
        for awg_channel in self._awg_channels:
            frequency = self._awg_parameters[awg_channel]["frequency"]
            amplitude = self._awg_parameters[awg_channel]["amplitude"]
            segment.add_awg_function(awg_channel, AWGSinePulse(frequency, amplitude))
        for ttl_channel in self._ttl_channels:
            state = self._ttl_parameters[ttl_channel]
            if state:
                segment.add_ttl_function(ttl_channel, TTLOn())
            else:
                segment.add_ttl_function(ttl_channel, TTLOff())
        self._sine_segments[name] = segment

    def _update_sine_data(self):
        self._current_segments.insert_segments(self._sine_segments)
        name = f"__sine_{self._next_sine_segment}"
        for kk, hcard in enumerate(self._hcards):
            self._write_segment(
                hcard,
                self._next_sine_segment,
                self._sine_segments[name],
            )
            seg = self._current_segments.single_board_segments[kk].segments[self._next_sine_segment]
            for ll in range(2):
                if self._next_sine_segment == ll:
                    next_step = self._sine_segment_steps[kk][ll]
                else:
                    next_step = self._sine_segment_steps[kk][1 - ll]
                self._set_segment_step_memory(
                    hcard,
                    step_number=self._sine_segment_steps[kk][ll],
                    segment_number=ll,
                    next_step=next_step,
                    loops=1,
                    end="end_loop",
                )

    def _set_segment_steps(self, hcard):
        last_step = -1
        card_index = self._hcards.index(hcard)
        for step_info in self._current_segments.single_board_segments[card_index].steps:
            self._set_segment_step_memory(hcard, *step_info)
        last_step = step_info[0]

        self._sine_segment_steps[card_index] = [last_step + 1, last_step + 2]
        for ll in range(2):
            self._set_segment_step_memory(
                hcard,
                step_number=self._sine_segment_steps[card_index][ll],
                segment_number=ll,
                next_step=self._sine_segment_steps[card_index][ll],
                loops=1,
                end="end_loop",
            )

    def _write_segment(self, hcard, segment_number: int, segment: Segment):
        self._set_sequence_write_segment(hcard, segment_number)

        duration = segment.actual_duration
        size = int(round(duration.to("s").magnitude * self._sample_rate))
        self._set_sequence_write_segment_size(hcard, size)

        card_index = self._hcards.index(hcard)
        awg_channels = [4 * card_index + kk for kk in range(4)]
        ttl_awg_map = {3 * card_index + kk: 4 * card_index + kk for kk in range(3)}
        data = segment.get_sample_data(
            awg_channels,
            ttl_awg_map,
            np.arange(size),
            self._sample_rate,
        )
        data_length = self._define_transfer_buffer(hcard, card_index, data)
        self._set_data_ready_to_transfer(hcard, data_length)
        self._start_dma_transfer(hcard)
        self._wait_dma_transfer(hcard)
        self._segment_name_maps[card_index][segment.name] = segment_number

    # public functions
    def setup_segments(self, segments: AllBoardSegments):
        """Sets up segments and segment steps."""
        if self._number_of_cards > 1:
            # TTL trigger for all other boards.
            segments.single_board_segments[0]._segments["__start"].add_ttl_function(
                0, TTLOn()
            )
        self._current_segments = segments
        self._segment_name_maps = {}  # maps segment names to indices in AWG memory

        for kk, hcard in enumerate(self._hcards):
            self._set_mode(hcard, "sequence")
            segments_this_board = self._current_segments.single_board_segments[kk].segments
            min_num_segments = int(np.power(2, np.ceil(np.log2(len(segments_this_board)))))
            self._set_sequence_max_segments(hcard, min_num_segments)
            self._segment_name_maps[kk] = {}

            segment_number = -1
            for segment_number in range(len(segments_this_board)):
                self._write_segment(hcard, segment_number, segments_this_board[segment_number])
        self.setup_segment_steps_only()
        self.write_all_setup()

    def setup_segment_steps_only(self):
        """Only sets up the steps of a sequence.

        Useful if only segment step order is changed.
        self.write_all_setup() must be called afterwards to validate.
        """
        self._sine_segment_steps = {}
        for kk, hcard in enumerate(self._hcards):
            self._set_segment_steps(hcard)

    def change_segment(self, card_index, segment_name):
        """Reprograms one of the segment of a sequence that is already set up.

        Useful if only some of the segments are changed.
        self.write_all_setup() must be called afterwards to validate.

        This still does not work.
        """
        index = self._segment_name_maps[card_index][segment_name]
        segment = None
        for s in self._current_segments.single_board_segments[card_index].segments:
            if s.name == segment_name:
                segment = s
                break
        self._write_segment(self._hcards[card_index], index, segment)

    def write_all_setup(self):
        """Writes the setup to the devices."""
        for hcard in self._hcards:
            self._write_setup(hcard)

    def start_sequence(self, first_card_only = False):
        """Starts the sequence."""
        if self._sine_segment_running:
            self.stop_sine_outputs()
        if not first_card_only:
            for hcard in reversed(self._hcards):  # start the first card the last to trigger other cards
                self._set_segment_start_step(hcard, 0)
                self._start(hcard)
                self._enable_triggers(hcard)
        else:
            self._set_segment_start_step(self._hcards[0], 0)
            self._start(self._hcards[0])
            self._enable_triggers(self._hcards[0])

    def wait_for_sequence_complete(self, first_card_only = False):
        """Waits for the programmed sequence to be done."""
        if not first_card_only:
            for hcard in self._hcards:
                self._wait_for_complete(hcard)
        else:
            self._wait_for_complete(self._hcards[0])

    def stop_sequence(self, first_card_only = False):
        """Stops the sequence."""
        if not first_card_only:
            for hcard in self._hcards:
                self._stop(hcard)
        else:
            self._stop(self._hcards[0])

    def start_sine_outputs(self):
        """Starts the sine output mode."""
        if self._sine_segment_running:
            raise Exception("Sine outputs are already on.")
        for kk, hcard in enumerate(self._hcards):
            self._set_segment_start_step(hcard, self._sine_segment_steps[kk][self._next_sine_segment])
            self._set_trigger_or_mask(hcard, pyspcm.SPC_TMASK_SOFTWARE)

        for hcard in self._hcards:
            self._start(hcard)
            self._enable_triggers(hcard)
        self._sine_segment_running = True

    def set_sine_output(
        self,
        awg_channel: int,
        frequency: Union[float, Q_],
        amplitude: int,
    ):
        """Sets the sine output parameters on a channel."""
        if self._sine_segment_running:
            self._next_sine_segment = 1 - self._next_sine_segment
        self._awg_parameters[awg_channel]["frequency"] = frequency
        self._awg_parameters[awg_channel]["amplitude"] = amplitude
        self._set_sine_segment()
        self._update_sine_data()

    def set_ttl_output(self, ttl_channel: int, state: bool):
        """Sets the TTL output on a channel."""
        if self._sine_segment_running:
            self._next_sine_segment = 1 - self._next_sine_segment
        self._ttl_parameters[ttl_channel] = state
        self._set_sine_segment()
        self._update_sine_data()

    def stop_sine_outputs(self):
        """Stops the sine output mode."""
        if not self._sine_segment_running:
            raise Exception("Sine outputs are already off.")
        self._sine_segment_running = False
        self._stop(self._hcards[0])
        self._set_trigger_or_mask(self._hcards[0], pyspcm.SPC_TMASK_SOFTWARE)
        for hcard in self._hcards[1:]:
            self._stop(hcard)
            self._set_trigger_or_mask(hcard, pyspcm.SPC_TMASK_EXT0)

    def get_and_clear_error(self):
        """Get and clear the error."""
        for hcard in self._hcards:
            print(hcard, self._get_error_information(hcard))
