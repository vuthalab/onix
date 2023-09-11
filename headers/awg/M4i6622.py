from typing import List, Literal, Optional, Tuple, Union

import numpy as np
import onix.headers.awg.pyspcm as pyspcm
from onix.headers.awg.spcm_tools import pvAllocMemPageAligned
from onix.sequences.sequence import (AWGSinePulse, Segment, Sequence, TTLOff,
                                     TTLOn)
from onix.units import Q_, ureg

CHANNEL_TYPE = Literal[0, 1, 2, 3]
MAX_SAMPLE_RATE = 62500000


class M4i6622:
    """Driver for the M4i6622 arbitrary waveform generator.

    Mostly it focuses on the sequence replay mode of the card. When not running a user-defined
    sequence, it can output sine waves with user-defined frequency and amplitude on all channels.

    Code is written for a PCI-e M4i6622 card. It may work for other M4i cards with modification.
    """

    def __init__(
        self,
        address: str = "/dev/spcm0",
        external_clock_frequency: Optional[int] = None,
    ):
        self._hcard = pyspcm.spcm_hOpen(
            pyspcm.create_string_buffer(address.encode("ascii"))
        )
        if self._hcard is None:
            raise Exception("No card is found.")

        self._reset()
        self._bytes_per_sample = self._get_bytes_per_sample()

        if external_clock_frequency is not None:
            self._set_clock_mode("external_reference")
            self._set_external_clock_frequency(external_clock_frequency)
        else:
            self._set_clock_mode("internal_pll")

        self._set_sample_rate()
        self._sample_rate = self._get_sample_rate()
        self._set_trigger_or_mask(pyspcm.SPC_TMASK_SOFTWARE)
        self._set_trigger_and_mask(pyspcm.SPC_TMASK_NONE)

        self._awg_channels = list(range(4))
        self._ttl_channels = list(range(3))
        self._select_channels(self._awg_channels)
        for awg_channel in self._awg_channels:
            self._enable_channel(awg_channel)
            self._set_channel_amplitude(awg_channel)
            self._set_channel_filter(awg_channel)

        # Maps of TTL channels mixing with AWG channels
        self._ttl_awg_map = {0: 0, 1: 1, 2: 2}
        for ttl_channel in self._ttl_awg_map:
            mode = pyspcm.SPCM_XMODE_DIGOUT
            mode = mode | getattr(
                pyspcm, f"SPCM_XMODE_DIGOUTSRC_CH{self._ttl_awg_map[ttl_channel]}"
            )
            mode = mode | pyspcm.SPCM_XMODE_DIGOUTSRC_BIT15
            self._set_multi_purpose_io_mode(ttl_channel, mode)

        # implements the sine segments.
        self._next_sine_segment = 0
        self._awg_parameters = {}
        for channel in self._awg_channels:
            self._awg_parameters[channel] = {"frequency": 0 * ureg.Hz, "amplitude": 0}
        self._ttl_parameters = [False, False, False]
        self._sine_segment_duration = 100 * ureg.us
        self._sine_segments = {
            "__sine_0": Segment("__sine_0", duration=self._sine_segment_duration),
            "__sine_1": Segment("__sine_1", duration=self._sine_segment_duration),
        }
        self._sine_segment_running = False
        self._set_sine_segment()
        self.setup_sequence(Sequence())

    # device methods
    def _get_bytes_per_sample(self) -> int:
        value = pyspcm.int32(0)
        ret = pyspcm.spcm_dwGetParam_i32(
            pyspcm.SPC_MIINST_BYTESPERSAMPLE, pyspcm.byref(value)
        )
        if ret != pyspcm.ERR_OK:
            raise Exception(f"Get bytes per sample failed with code {ret}.")
        return value.value

    def _select_channels(self, channels: List[CHANNEL_TYPE]):
        if len(channels) == 3:
            raise ValueError("Cannot enable 3 channels. Enable 4 channels instead.")
        value = 0
        for channel in channels:
            value = value | getattr(pyspcm, f"CHANNEL{channel}")
        ret = pyspcm.spcm_dwSetParam_i64(self._hcard, pyspcm.SPC_CHENABLE, value)
        if ret != pyspcm.ERR_OK:
            raise Exception(f"Select channels failed with code {ret}.")

    def _enable_channel(self, channel: CHANNEL_TYPE, enabled: bool = True):
        if enabled:
            value = pyspcm.int64(1)
        else:
            value = pyspcm.int64(0)
        ret = pyspcm.spcm_dwSetParam_i64(
            self._hcard, getattr(pyspcm, f"SPC_ENABLEOUT{channel}"), value
        )
        if ret != pyspcm.ERR_OK:
            raise Exception(f"Enable channel failed with code {ret}.")

    def _set_channel_amplitude(self, channel: CHANNEL_TYPE, amplitude_mV: int = 2500):
        ret = pyspcm.spcm_dwSetParam_i32(
            self._hcard,
            getattr(pyspcm, f"SPC_AMP{channel}"),
            pyspcm.int32(amplitude_mV),
        )
        if ret != pyspcm.ERR_OK:
            raise Exception(f"Set channel amplitude failed with code {ret}.")

    def _set_channel_filter(self, channel: CHANNEL_TYPE, filter: int = 0):
        ret = pyspcm.spcm_dwSetParam_i32(
            self._hcard, getattr(pyspcm, f"SPC_FILTER{channel}"), pyspcm.int32(filter)
        )
        if ret != pyspcm.ERR_OK:
            raise Exception(f"Set channel filter failed with code {ret}.")

    def _set_mode(
        self,
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
        ret = pyspcm.spcm_dwSetParam_i32(self._hcard, pyspcm.SPC_CARDMODE, value)
        if ret != pyspcm.ERR_OK:
            raise Exception(f"Set mode failed with code {ret}.")

    def _reset(self):
        """Resets the card."""
        ret = pyspcm.spcm_dwSetParam_i32(
            self._hcard, pyspcm.SPC_M2CMD, pyspcm.M2CMD_CARD_RESET
        )
        if ret != pyspcm.ERR_OK:
            raise Exception(f"Reset failed with code {ret}.")

    def _write_setup(self):
        """Writes the setup without starting the card."""
        ret = pyspcm.spcm_dwSetParam_i32(
            self._hcard, pyspcm.SPC_M2CMD, pyspcm.M2CMD_CARD_WRITESETUP
        )
        if ret != pyspcm.ERR_OK:
            raise Exception(f"Write setup failed with code {ret}.")

    def _start(self):
        """Writes the setup and starts the card."""
        ret = pyspcm.spcm_dwSetParam_i32(
            self._hcard, pyspcm.SPC_M2CMD, pyspcm.M2CMD_CARD_START
        )
        if ret != pyspcm.ERR_OK:
            raise Exception(f"Start card failed with code {ret}.")

    def _enable_triggers(self):
        """Enables detecting triggers."""
        ret = pyspcm.spcm_dwSetParam_i32(
            self._hcard, pyspcm.SPC_M2CMD, pyspcm.M2CMD_CARD_ENABLETRIGGER
        )
        if ret != pyspcm.ERR_OK:
            raise Exception(f"Enable triggers failed with code {ret}.")

    def _force_trigger(self):
        """Sends a software trigger."""
        ret = pyspcm.spcm_dwSetParam_i32(
            self._hcard, pyspcm.SPC_M2CMD, pyspcm.M2CMD_CARD_FORCETRIGGER
        )
        if ret != pyspcm.ERR_OK:
            raise Exception(f"Force trigger failed with code {ret}.")

    def _disable_triggers(self):
        """Disables detecting triggers."""
        ret = pyspcm.spcm_dwSetParam_i32(
            self._hcard, pyspcm.SPC_M2CMD, pyspcm.M2CMD_CARD_DISABLETRIGGER
        )
        if ret != pyspcm.ERR_OK:
            raise Exception(f"Disable triggers failed with code {ret}.")

    def _stop(self):
        """Stops the current run of the card."""
        ret = pyspcm.spcm_dwSetParam_i32(
            self._hcard, pyspcm.SPC_M2CMD, pyspcm.M2CMD_CARD_STOP
        )
        if ret != pyspcm.ERR_OK:
            raise Exception(f"Stop card failed with code {ret}.")

    def _wait_for_trigger(self):
        """Waits until the first trigger event has been detected by the card."""
        ret = pyspcm.spcm_dwSetParam_i32(
            self._hcard, pyspcm.SPC_M2CMD, pyspcm.M2CMD_CARD_WAITTRIGGER
        )
        if ret != pyspcm.ERR_OK:
            raise Exception(f"Wait for trigger failed with code {ret}.")

    def _wait_for_complete(self):
        """Waits until the card has completed the current run."""
        ret = pyspcm.spcm_dwSetParam_i32(
            self._hcard, pyspcm.SPC_M2CMD, pyspcm.M2CMD_CARD_WAITREADY
        )
        if ret != pyspcm.ERR_OK:
            raise Exception(f"Wait for complete failed with code {ret}.")

    def _define_transfer_buffer(
        self,
        data: np.ndarray,
        transfer_offset: int = 0,
    ):
        aligned_buffer = pvAllocMemPageAligned(len(data) * 2)  # 2 bytes per sample.
        data_buffer = data_buffer.astype(np.int16).tobytes()
        aligned_buffer[:] = data_buffer
        ret = pyspcm.spcm_dwDefTransfer_i64(
            self._hcard,
            pyspcm.SPCM_BUF_DATA,
            pyspcm.SPCM_DIR_PCTOCARD,
            pyspcm.uint32(0),
            aligned_buffer,
            pyspcm.uint64(transfer_offset),
            pyspcm.uint64(len(data_buffer)),
        )
        if ret != pyspcm.ERR_OK:
            raise Exception(f"Define transfer buffer failed with code {ret}.")

    def _start_dma_transfer(self):
        ret = pyspcm.spcm_dwSetParam_i32(
            self._hcard, pyspcm.SPC_M2CMD, pyspcm.M2CMD_DATA_STARTDMA
        )
        if ret != pyspcm.ERR_OK:
            raise Exception(f"Stop DMA transfer failed with code {ret}.")

    def _wait_dma_transfer(self):
        ret = pyspcm.spcm_dwSetParam_i32(
            self._hcard, pyspcm.SPC_M2CMD, pyspcm.M2CMD_DATA_WAITDMA
        )
        if ret != pyspcm.ERR_OK:
            raise Exception(f"Wait DMA transfer failed with code {ret}.")

    def _stop_dma_transfer(self):
        ret = pyspcm.spcm_dwSetParam_i32(
            self._hcard, pyspcm.SPC_M2CMD, pyspcm.M2CMD_DATA_STOPDMA
        )
        if ret != pyspcm.ERR_OK:
            raise Exception(f"Stop DMA transfer failed with code {ret}.")

    def _set_memory_size(self, samples_per_channel: int):
        ret = pyspcm.spcm_dwSetParam_i64(
            self._hcard, pyspcm.SPC_MEMSIZE, pyspcm.int64(samples_per_channel)
        )
        if ret != pyspcm.ERR_OK:
            raise Exception(f"Set memory size failed with code {ret}.")

    def _set_segment_size(self, samples_per_segment: int):
        ret = pyspcm.spcm_dwSetParam_i64(
            self._hcard, pyspcm.SPC_SEGMENTSIZE, pyspcm.int64(samples_per_segment)
        )
        if ret != pyspcm.ERR_OK:
            raise Exception(f"Set segment size failed with code {ret}.")

    def _set_number_of_loops(self, loops: int):
        ret = pyspcm.spcm_dwSetParam_i64(
            self._hcard, pyspcm.SPC_LOOPS, pyspcm.int64(loops)
        )
        if ret != pyspcm.ERR_OK:
            raise Exception(f"Set number of loops failed with code {ret}.")

    def _set_clock_mode(
        self,
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
        ret = pyspcm.spcm_dwSetParam_i32(self._hcard, pyspcm.SPC_CLOCKMODE, value)
        if ret != pyspcm.ERR_OK:
            raise Exception(f"Set clock mode failed with code {ret}.")

    def _get_sample_rate(self) -> int:
        value = pyspcm.int64(0)
        ret = pyspcm.spcm_dwSetParam_i64(
            self._hcard, pyspcm.SPC_SAMPLERATE, pyspcm.byref(value)
        )
        if ret != pyspcm.ERR_OK:
            raise Exception(f"Set sample rate failed with code {ret}.")
        return value.value

    def _set_sample_rate(self, sample_rate: int = MAX_SAMPLE_RATE):
        ret = pyspcm.spcm_dwSetParam_i64(
            self._hcard, pyspcm.SPC_SAMPLERATE, pyspcm.int64(sample_rate)
        )
        if ret != pyspcm.ERR_OK:
            raise Exception(f"Set sample rate failed with code {ret}.")

    def _set_external_clock_frequency(self, clock_frequency: int):
        ret = pyspcm.spcm_dwSetParam_i32(
            self._hcard, pyspcm.SPC_REFERENCECLOCK, pyspcm.int32(clock_frequency)
        )
        if ret != pyspcm.ERR_OK:
            raise Exception(f"Set external clock frequency failed with code {ret}.")

    def _set_trigger_or_mask(self, trigger_mask: int):
        ret = pyspcm.spcm_dwSetParam_i32(
            self._hcard, pyspcm.SPC_TRIG_ORMASK, pyspcm.int32(trigger_mask)
        )
        if ret != pyspcm.ERR_OK:
            raise Exception(f"Set trigger OR mask failed with code {ret}.")

    def _set_trigger_and_mask(self, trigger_mask: int):
        ret = pyspcm.spcm_dwSetParam_i32(
            self._hcard, pyspcm.SPC_TRIG_ANDMASK, pyspcm.int32(trigger_mask)
        )
        if ret != pyspcm.ERR_OK:
            raise Exception(f"Set trigger AND mask failed with code {ret}.")

    # TODO: implement external trigger EXT0 and EXT1 functions

    def _set_multi_purpose_io_mode(self, line_number: Literal[0, 1, 2], mode: int):
        ret = pyspcm.spcm_dwSetParam_i32(
            self._hcard,
            getattr(pyspcm, f"SPCM_X{line_number}_MODE"),
            pyspcm.int32(mode),
        )
        if ret != pyspcm.ERR_OK:
            raise Exception(f"Set multiple purpose io mode failed with code {ret}.")

    def _get_multi_purpose_io_output(self) -> Tuple[bool, bool, bool]:
        mode = pyspcm.int32(0)
        ret = pyspcm.spcm_dwGetParam_i32(
            self._hcard, pyspcm.SPCM_XX_ASYNCIO, pyspcm.byref(mode)
        )
        if ret != pyspcm.ERR_OK:
            raise Exception(f"Get multi purpose io output failed with code {ret}.")
        return (mode.value & 1 != 0, mode.value & 2 != 0, mode.value & 4 != 0)

    def _set_multi_purpose_io_output(
        self, x0_state: bool, x1_state: bool, x2_state: bool
    ):
        mode = 0
        if x0_state:
            mode += 1
        if x1_state:
            mode += 2
        if x2_state:
            mode += 4
        ret = pyspcm.spcm_dwSetParam_i32(
            self._hcard, pyspcm.SPCM_XX_ASYNCIO, pyspcm.int32(mode)
        )
        if ret != pyspcm.ERR_OK:
            raise Exception(f"Set multi purpose io output failed with code {ret}.")

    def _set_sequence_max_segments(self, segments: int):
        ret = pyspcm.spcm_dwSetParam_i32(
            self._hcard, pyspcm.SPC_SEQMODE_MAXSEGMENTS, pyspcm.int32(segments)
        )
        if ret != pyspcm.ERR_OK:
            raise Exception(f"Set sequence max segments failed with code {ret}.")

    def _set_sequence_write_segment(self, segment_number: int):
        ret = pyspcm.spcm_dwSetParam_i32(
            self._hcard, pyspcm.SPC_SEQMODE_WRITESEGMENT, pyspcm.int32(segment_number)
        )
        if ret != pyspcm.ERR_OK:
            raise Exception(f"Set sequence write segment failed with code {ret}.")

    def _set_sequence_write_segment_size(self, segment_size: int):
        ret = pyspcm.spcm_dwSetParam_i32(
            self._hcard, pyspcm.SPC_SEQMODE_SEGMENTSIZE, pyspcm.int32(segment_size)
        )
        if ret != pyspcm.ERR_OK:
            raise Exception(f"Set sequence write segment size failed with code {ret}.")

    def _set_sequence_step_memory(
        self,
        step_number: int,
        segment_number: int,
        next_step: int,
        loops: int,
        end: Literal["end_loop", "end_loop_on_trig", "end_sequence"] = "end_loop",
    ):
        register = pyspcm.SPC_SEQMODE_STEPMEM0 + step_number
        value = ((end | loops) << 32) | (next_step << 16) | segment_number
        ret = pyspcm.spcm_dwSetParam_i64(self._hcard, register, value)
        if ret != pyspcm.ERR_OK:
            raise Exception(f"Set sequence step memory failed with code {ret}.")

    def _get_sequence_start_step(self) -> int:
        value = pyspcm.int32(0)
        ret = pyspcm.spcm_dwSetParam_i32(
            self._hcard, pyspcm.SPC_SEQMODE_STARTSTEP, pyspcm.byref(value)
        )
        if ret != pyspcm.ERR_OK:
            raise Exception(f"Get sequence start step failed with code {ret}.")
        return value.value

    def _set_sequence_start_step(self, start_step_number: int):
        ret = pyspcm.spcm_dwSetParam_i32(
            self._hcard, pyspcm.SPC_SEQMODE_STARTSTEP, pyspcm.int32(start_step_number)
        )
        if ret != pyspcm.ERR_OK:
            raise Exception(f"Set sequence start step failed with code {ret}.")

    def _get_sequence_current_step(self) -> int:
        value = pyspcm.int32(0)
        ret = pyspcm.spcm_dwSetParam_i32(
            self._hcard, pyspcm.SPC_SEQMODE_STATUS, pyspcm.byref(value)
        )
        if ret != pyspcm.ERR_OK:
            raise Exception(f"Get sequence current step failed with code {ret}.")
        return value.value

    # helper functions
    def _set_sine_segment(self):
        name = f"__sine_{self._next_sine_segment}"
        segment = Segment(duration=self._sine_segment_duration)
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
            self._set_sequence_step_memory(
                step_number=self._sine_segment_steps[kk],
                segment_number=kk,
                next_step=next_step,
                loops=1,
                end="end_loop",
            )

    def _set_sequence_steps(self):
        last_step = 0
        for step_info in self._current_sequence.steps:
            self._set_sequence_step_memory(*step_info)
            last_step = step_info[0]

        self._sine_segment_steps = [last_step + 1, last_step + 2]
        for kk in range(2):
            self._set_sequence_step_memory(
                step_number=self._sine_segment_steps[kk],
                segment_number=kk,
                next_step=self._sine_segment_steps[kk],
                loops=1,
                end="end_loop",
            )

    def _write_segment(self, segment_number: int, segment: Segment):
        self._set_sequence_write_segment(segment_number)

        duration = segment.duration
        size = int(duration * self._sample_rate)
        size = (size + 31) // 32 * 32  # the sample size must be a multiple of 32.
        if size < 96:
            size = 96  # minimum 96 samples for 4 channels.
        self._set_sequence_write_segment_size(size)

        data = segment.get_sample_data(
            self._awg_channels,
            self._ttl_awg_map,
            np.arange(size),
            self._sample_rate,
        )
        self._define_transfer_buffer(data)
        self._start_dma_transfer()
        self._wait_dma_transfer()

    # public functions
    def setup_sequence(self, sequence: Sequence):
        sequence.insert_segments(self._sine_segments)
        self._current_sequence = sequence

        self._set_mode("sequence")
        segments = self._current_sequence.segments
        min_num_segments = int(np.power(2, np.ceil(np.log2(len(segments)))))
        self._set_sequence_max_segments(min_num_segments)

        for segment_number in range(len(segments)):
            self._write_segment(segment_number, segments[segment_number])

        self._set_sequence_steps()
        self._write_setup()
        self._enable_triggers()

    def start_sequence(self):
        if self._sine_segment_running:
            self._stop()
        self._set_sequence_start_step(0)
        self._start()

    def wait_for_sequence_complete(self):
        self._wait_for_complete()

    def stop_sequence(self):
        self._stop()

    def start_sine_outputs(self):
        if self._sine_segment_running:
            raise Exception("Sine outputs are already on.")
        self._wait_for_complete()
        self._set_sequence_start_step(self._sine_segment_steps[self._next_sine_segment])
        self._start()
        self._sine_segment_running = True

    def set_sine_output(
        self,
        awg_channel: int,
        frequency: Union[float, Q_],
        amplitude: int,
    ):
        self._awg_parameters[awg_channel]["frequency"] = frequency
        self._awg_parameters[awg_channel]["amplitude"] = amplitude
        self._set_sine_segment()
        self._update_sine_data()
        self._next_sine_segment = 1 - self._next_sine_segment

    def set_ttl_output(self, ttl_channel: int, state: bool):
        self._ttl_parameters[ttl_channel] = state
        self._set_sine_segment()
        self._update_sine_data()
        self._next_sine_segment = 1 - self._next_sine_segment

    def stop_sine_outputs(self):
        if self._sine_segment_running:
            raise Exception("Sine outputs are already on.")
        self._sine_segment_running = False
        self._stop()
