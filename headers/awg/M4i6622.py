# TODO: after stop sine output cannot run new sequence
# TODO: start_sequence incorrectly starts sine output on the first board.

from typing import Literal, Optional, Union

import numpy as np
import onix.headers.awg.pyspcm as pyspcm

from onix.headers.awg.spcm_tools import pvAllocMemPageAligned
from onix.sequences.sequence import (AWGSinePulse, Segment, Sequence, TTLOff,
                                     TTLOn)
from onix.units import Q_, ureg

CHANNEL_TYPE = Literal[0, 1, 2, 3]
MAX_SAMPLE_RATE = 625000000


class M4i6622:
    """Header for the M4i6622 arbitrary waveform generator.

    Mostly it focuses on the sequence replay mode of the card. When not running a user-defined
    sequence, it can output sine waves with user-defined frequency and amplitude on all channels.

    Code is written for a PCIe M4i6622 card. It may work for other M4i cards with modification.

    When using the public functions of this header, all 4 AWG and 3 TTL channels are always used.
    The amplitude accuracy of channels 0 to 2 is reduced from 16 bits to 15 bits to enable
    the TTL channels. Highest sample rate of 625 M/s is used.

    External clock is not tested.

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
        m4i.setup_sequence(...)  # see onix.sequences.sequence.Sequence class.

        # the code below can be run without setting up the sequence again.
        for kk in range(repeats):
            m4i.start_sequence()
            m4i.wait_for_sequence_complete()
        m4i.stop_sequence()

    It can switch between the sine output mode and the pulse sequence mode.
    It should remember the previous sequence loaded and the sine outputs set.
    Therefore, the setup functions don't need to be called again unless the user
    wants to change the sequence or the sine output.

    When switching from sine output to a pulse sequence, it automatically turns off the
    sine output if on, and will not turn the sine output back on automatically at the end
    of the sequence.

    Update:
        Added capability to control multiple cards to provide more rf and digital channels.
        To use multiple cards, initialize the class with a list of strs.
        It assumes all cards are M4i6622.
        Assumes that the star-hub option is not used, and the GPIO output channel 0 of the first
        card is connected to the trigger ext0 of all other cards.

    Update 2024-07-03:
        Allows only modifying the order of the sequence or only change part of the sequence using
        setup_sequence_steps_only, change_segment, and write_all_setup.
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
        self._segment_name_map = {}

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
        self.setup_sequence(Sequence())

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

    def _set_sequence_step_memory(
        self,
        hcard,
        step_number: int,
        segment_number: int,
        next_step: int,
        loops: int,
        end: Literal["end_loop", "end_loop_on_trig", "end_sequence"] = "end_loop",
    ):
        """Sets the parameters for a sequence step.

        For some reason that the last "end_sequnce" step always don't output.
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
            raise Exception(f"Set sequence step memory failed with code {ret}.")

    def _get_sequence_start_step(self, hcard) -> int:
        value = pyspcm.int32(0)
        ret = pyspcm.spcm_dwGetParam_i32(
            hcard, pyspcm.SPC_SEQMODE_STARTSTEP, pyspcm.byref(value)
        )
        if ret != pyspcm.ERR_OK:
            raise Exception(f"Get sequence start step failed with code {ret}.")
        return value.value

    def _set_sequence_start_step(self, hcard, start_step_number: int):
        ret = pyspcm.spcm_dwSetParam_i32(
            hcard, pyspcm.SPC_SEQMODE_STARTSTEP, pyspcm.int32(start_step_number)
        )
        if ret != pyspcm.ERR_OK:
            raise Exception(f"Set sequence start step failed with code {ret}.")

    def _get_sequence_current_step(self, hcard) -> int:
        value = pyspcm.int32(0)
        ret = pyspcm.spcm_dwSetParam_i32(
            hcard, pyspcm.SPC_SEQMODE_STATUS, pyspcm.byref(value)
        )
        if ret != pyspcm.ERR_OK:
            raise Exception(f"Get sequence current step failed with code {ret}.")
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
        self._current_sequence.insert_segments(self._sine_segments)
        self._write_segment(
            self._next_sine_segment,
            self._current_sequence.segments[self._next_sine_segment],
        )
        for kk in range(2):
            if self._next_sine_segment == kk:
                next_step = self._sine_segment_steps[kk]
            else:
                next_step = self._sine_segment_steps[1 - kk]
            for hcard in self._hcards:
                self._set_sequence_step_memory(
                    hcard,
                    step_number=self._sine_segment_steps[kk],
                    segment_number=kk,
                    next_step=next_step,
                    loops=1,
                    end="end_loop",
                )

    def _set_sequence_steps(self):
        last_step = -1
        for step_info in self._current_sequence.steps:
            for hcard in self._hcards:
                self._set_sequence_step_memory(hcard, *step_info)
            last_step = step_info[0]

        self._sine_segment_steps = [last_step + 1, last_step + 2]
        for kk in range(2):
            for hcard in self._hcards:
                self._set_sequence_step_memory(
                    hcard,
                    step_number=self._sine_segment_steps[kk],
                    segment_number=kk,
                    next_step=self._sine_segment_steps[kk],
                    loops=1,
                    end="end_loop",
                )

    def _write_segment(self, segment_number: int, segment: Segment):
        for hcard in self._hcards:
            self._set_sequence_write_segment(hcard, segment_number)

        duration = segment.duration
        size = int(duration.to("s").magnitude * self._sample_rate)
        size = (size + 31) // 32 * 32  # the sample size must be a multiple of 32.
        if size < 96:
            size = 96  # minimum 96 samples for 4 channels.
        for hcard in self._hcards:
            self._set_sequence_write_segment_size(hcard, size)

        for index, hcard in enumerate(self._hcards):
            awg_channels = [4 * index + kk for kk in range(4)]
            ttl_awg_map = {3 * index + kk: 4 * index + kk for kk in range(3)}
            data = segment.get_sample_data(
                awg_channels,
                ttl_awg_map,
                np.arange(size),
                self._sample_rate,
            )
            data_length = self._define_transfer_buffer(hcard, index, data)
            self._set_data_ready_to_transfer(hcard, data_length)
            self._start_dma_transfer(hcard)
        for hcard in self._hcards:
            self._wait_dma_transfer(hcard)
        self._segment_name_map[segment.name] = segment_number

    # public functions
    def setup_sequence(self, sequence: Sequence):
        """Sets up a sequence """
        if self._number_of_cards > 1:
            sequence._segments["__start"].add_ttl_function(0, TTLOn())
        # sequence.insert_segments(self._sine_segments)
        # above line commented to avoid occupying two segments in the AWG memory
        # however it means that when a sequence is already set up we cannot run sine waves.
        self._current_sequence = sequence

        for hcard in self._hcards:
            self._set_mode(hcard, "sequence")
        segments = self._current_sequence.segments
        min_num_segments = int(np.power(2, np.ceil(np.log2(len(segments)))))
        for hcard in self._hcards:
            self._set_sequence_max_segments(hcard, min_num_segments)
            self._segment_name_map = {}

        segment_number = -1
        for segment_number in range(len(segments)):
            self._write_segment(segment_number, segments[segment_number])

        self.setup_sequence_steps_only()
        self.write_all_setup()

    def setup_sequence_steps_only(self):
        """Only sets up the steps of a sequence.
        
        Useful if only sequence order is changed.
        self.write_all_setup() must be called afterwards to validate.
        """
        self._set_sequence_steps()

    def change_segment(self, segment_name):
        """Reprograms one of the segment of a sequence that is already set up.
        
        Useful if only some of the segments are changed.
        self.write_all_setup() must be called afterwards to validate.

        This still does not work.
        """
        index = self._segment_name_map[segment_name]
        segment = None
        for s in self._current_sequence.segments:
            if s.name == segment_name:
                segment = s
                break
        self._write_segment(index, segment)

    def write_all_setup(self):
        """Writes the setup to the devices."""
        for hcard in self._hcards:
            self._write_setup(hcard)

    def start_sequence(self):
        """Starts the sequence."""
        if self._sine_segment_running:
            self.stop_sine_outputs()
        for hcard in reversed(self._hcards):  # start the first card the last to trigger other cards
            self._set_sequence_start_step(hcard, 0)
            self._start(hcard)
            self._enable_triggers(hcard)

    def wait_for_sequence_complete(self):
        """Waits for the programmed sequence to be done."""
        for hcard in self._hcards:
            self._wait_for_complete(hcard)

    def stop_sequence(self):
        """Stops the sequence."""
        for hcard in self._hcards:
            self._stop(hcard)

    def start_sine_outputs(self):
        """Starts the sine output mode."""
        if self._sine_segment_running:
            raise Exception("Sine outputs are already on.")
        for hcard in self._hcards:
            self._set_sequence_start_step(hcard, self._sine_segment_steps[self._next_sine_segment])
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

    """
    def replace_segment(self, new_segment_name, old_segment_name):
        segments = self._current_sequence.segments
        index_to_replace = segments.index(old_segment_name)
        self._write_segment(index_to_replace, new_segment_name)
    """
