import math
import os
import time
from typing import List, Literal, Optional, Tuple

import numpy as np
import onix.headers.awg.pyspcm as pyspcm
from onix.sequences.sequence import Sequence

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

    def setup_sequence(
        self,
        sequence: 
    ):

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
        data_buffer: np.ndarray,
        transfer_offset: int,
    ):
        data_buffer = data_buffer.astype(np.uint16).tobytes()
        ret = pyspcm.spcm_dwDefTransfer_i64(
            self._hcard,
            pyspcm.SPCM_BUF_DATA,
            pyspcm.SPCM_DIR_PCTOCARD,
            pyspcm.uint32(0),
            data_buffer,
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

    def _set_multi_propose_io_mode(self, line_number: Literal[0, 1, 2], mode: int):
        ret = pyspcm.spcm_dwSetParam_i32(
            self._hcard,
            getattr(pyspcm, f"SPCM_X{line_number}_MODE"),
            pyspcm.int32(mode),
        )
        if ret != pyspcm.ERR_OK:
            raise Exception(f"Set multiple propose io mode failed with code {ret}.")

    def _get_multiple_propose_io_output(self) -> Tuple[bool, bool, bool]:
        mode = pyspcm.int32(0)
        ret = pyspcm.spcm_dwGetParam_i32(
            self._hcard, pyspcm.SPCM_XX_ASYNCIO, pyspcm.byref(mode)
        )
        if ret != pyspcm.ERR_OK:
            raise Exception(f"Get multiple propose io output failed with code {ret}.")
        return (mode.value & 1 != 0, mode.value & 2 != 0, mode.value & 4 != 0)

    def _set_multiple_propose_io_output(
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
            raise Exception(f"Set multiple propose io output failed with code {ret}.")

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

    def 


# Put the sample rate in MHz when using this header


class M4i6622:
    def __init__(
        self,
        address=b"/dev/spcm0",
        channelNum=4,
        referenceClock=False,
        referenceClockFrequency=10000000,
        clockOut=False,
        pulseLength=2e-3,
        sampleRate=625,
        sequenceReplay=False,
        singleTrigger=False,
        multiTrigger=False,
        extTrigger=False,
        singleRestart=False,
        loop=1,
        numSegments=1,
        verbose=False,
        trigger=False,
        loop_list=[],
        next=[],
        conditions=[],
        initialStep=0,
        segTimes=[],
        triggerLevel=2000,
        filters=[0, 0, 0, 0],
        amplitudes=[2500, 2500, 2500, 2500],
        ttlOutOn=False,
        ttlOutChannel=[0],
        ttlSourceChannel=0,
    ):
        """
        Class to control the Spectrum M4i6622 AWG
        address: location of the card on the computer, default is /dev/spcm0
        channelNum: Number of channels used on the card. Default is 4
        - You cannot run 3 channels, if you do it will use 4 channels and run the last on 0, which may affect memory sizes.
        referenceClock: Presence of a reference clock, by default is False
        referenceClockFrequency: Frequency of the reference clock in Hz. By default is 10 MHz.
        clockOut: If you want a clock output from the M4i. By default is False.
        pulseLength: length of data in seconds stored on the board.
        sampleRate: In MHz, by default is the maximum value of 625MHz.
        Mode: All modes are by default set to false. Set the mode of operation you need to true, for example singleTrigger = True.
        loop: For every mode except sequenceReplay, how many times to loop your sequence. 0 corresponds to an infinite loop. This is N in my explanation of the modes above.
        numSegments: For every mode except sequenceReplay, how many segments to use
        trigger: Presence of an external trigger. If false runs the sequence automatically upon starting the card.
        triggerLevel: level of the trigger in mV. Default is 2000mV.
        filters: A list of whether or not to put a filter on each channel. 0 = off, 1 = on. By default is [0,0,0,0].
        amplitudes: The amplitude of each channel in mV. By default is 2500. Range is 80-2500mV

        For Sequence Replay we introduce the extra parameters:
        loop_list = [ ]: For every segment, how many times to loop through it.
        next = [ ]: What segment to play after having played this segment.
        Conditions = [ ]: List the conditions on which we leave one segment. They are
        - SPCSEQ_END: End the sequence after finishing this segment.
        - SPCSEQ_ENDLOOPONTRIG : Change to the next step only when there is a trigger.
        - SPCSEQ_ENDLOOPALWAYS : Finish with this segment and move on to the next.
        initialStep : The segment you want to start the sequence on. By default = 0.
        segTimes = [ ]: How long (in seconds) each segment should take.header_3_29

        When you run sequenceReplay on multiple channels at once, each segment must be the same length across the channels
        In sequenceReplay, you must divide the memory into 2^x number of segments, which may limit the amount of memory you have access to

        Reference clock frequencies can only go from 10 MHz to 1.25GHz, but cannot be between 750 to 757 MHz and 1125 to 1145 MHz
        """

        self.on = False
        self.verbose = verbose
        self.channelNum = channelNum
        self.referenceClock = referenceClock
        self.numSegments = int(numSegments)
        self.sampleRate = int(MEGA(sampleRate))
        self.trigger = trigger
        self.loop = loop  # how many times to loop a segment when not in sequenceReplay

        self.segTimes = segTimes
        self.initialStep = initialStep
        self.next = next
        self.conditions = conditions
        self.loop_list = loop_list  # list of how many times to loop each segment when in sequenceReplay

        self.sequenceReplay = sequenceReplay
        self.singleTrigger = singleTrigger
        self.multiTrigger = multiTrigger
        self.extTrigger = extTrigger
        self.singleRestart = singleRestart

        self.ttlOutOn = ttlOutOn
        self.ttlOutChannel = ttlOutChannel
        self.ttlSourceChannel = ttlSourceChannel

        if (
            self.sequenceReplay
        ):  # for sequenceReplay, pulseLength is not a parameter, so we add the lengths of each segment instead.
            pulseLength = sum(self.segTimes)

        if channelNum == 3:
            self.channelNum = 4
        else:
            self.channelNum = channelNum

        # calculate the number of samples needed for this waveform across all channels and round to an allowable 32 bit integer
        numSamples = self.sampleRate * pulseLength * channelNum
        numSamples = int(numSamples + (32 - numSamples % 32))
        self.numSamples = numSamples

        # Connect the Card
        self.hCard = spcm_hOpen(create_string_buffer(address))

        # Software reset the card to ensure its in a well-defined state
        spcm_dwSetParam_i32(self.hCard, SPC_M2CMD, M2CMD_CARD_RESET)

        if self.ttlOutOn:
            self.programTTLOut()
        else:
            for i in range(3):
                val = spcm_dwSetParam_i32(
                    self.hCard, SPCM_X0_MODE + i, SPCM_XMODE_DISABLE
                )
                if verbose:
                    print(f"TTL channel {i} disabled with error code {val}.")

        # Get byte count
        self.lBytesPerSample = int32(0)
        spcm_dwGetParam_i32(
            self.hCard, SPC_MIINST_BYTESPERSAMPLE, byref(self.lBytesPerSample)
        )

        # Read the Card Type, it's function and Serial Number
        self.lCardType = int32(0)
        spcm_dwGetParam_i32(self.hCard, SPC_PCITYP, byref(self.lCardType))
        self.lSerialNumber = int32(0)
        spcm_dwGetParam_i32(self.hCard, SPC_PCISERIALNO, byref(self.lSerialNumber))
        self.lFncType = int32(0)
        spcm_dwGetParam_i32(self.hCard, SPC_FNCTYPE, byref(self.lFncType))

        # Check if the card itself is valid
        Valid = self.checkCard()
        if Valid == False:
            exit()

        # Configure the reference clock if required
        if self.referenceClock == True:
            val = spcm_dwSetParam_i32(self.hCard, SPC_CLOCKMODE, SPC_CM_EXTREFCLOCK)
            # Set to reference clock mode
            if val != 0:
                print(f"Error when setting reference clock, error code: {val}\n")
            val = spcm_dwSetParam_i32(
                self.hCard, SPC_REFERENCECLOCK, referenceClockFrequency
            )
            # Reference clock that is fed in at the Clock Frequency
            if val != 0:
                print(
                    f"Error when setting reference clock frequency, error code: {val}\n"
                )
        else:
            if self.verbose:
                print("Using internal clock\n")

        # Set the Sample Rate
        if ((self.lCardType.value & TYP_SERIESMASK) == TYP_M4IEXPSERIES) or (
            (self.lCardType.value & TYP_SERIESMASK) == TYP_M4XEXPSERIES
        ):
            err_code = spcm_dwSetParam_i64(self.hCard, SPC_SAMPLERATE, self.sampleRate)
            val = int64(0)
            spcm_dwGetParam_i64(self.hCard, SPC_SAMPLERATE, byref(val))
            print("Sample Rate has been set to " + str(val.value / 1e6) + " MS/s.\n")
        else:
            spcm_dwSetParam_i64(self.hCard, SPC_SAMPLERATE, MEGA(1))
            print("ERROR: Incorrect card type. Sample Rate failed to be set.\n")

        # Set the clock output
        if clockOut == True:
            val = spcm_dwSetParam_i32(self.hCard, SPC_CLOCKOUT, 1)
            print("Clock Output On.\n")
        else:
            spcm_dwSetParam_i32(self.hCard, SPC_CLOCKOUT, 0)
            print("Clock Output Off.\n")

        # Setting up the channels.
        if self.channelNum == 1:
            spcm_dwSetParam_i64(self.hCard, SPC_CHENABLE, CHANNEL0)
        elif self.channelNum == 2:
            spcm_dwSetParam_i64(self.hCard, SPC_CHENABLE, CHANNEL0 | CHANNEL1)
        else:
            print("enabling all channels")
            spcm_dwSetParam_i64(
                self.hCard, SPC_CHENABLE, CHANNEL0 | CHANNEL1 | CHANNEL2 | CHANNEL3
            )

        channelEnable = [SPC_ENABLEOUT0, SPC_ENABLEOUT1, SPC_ENABLEOUT2, SPC_ENABLEOUT3]
        amplitudeList = [SPC_AMP0, SPC_AMP1, SPC_AMP2, SPC_AMP3]
        filterList = [SPC_FILTER0, SPC_FILTER1, SPC_FILTER2, SPC_FILTER3]

        for i in range(0, self.channelNum, 1):
            spcm_dwSetParam_i64(self.hCard, channelEnable[i], 1)  # Enabling the channel
            spcm_dwSetParam_i32(
                self.hCard, amplitudeList[i], int32(amplitudes[i])
            )  # Setting the max amplitude
            spcm_dwSetParam_i32(
                self.hCard, filterList[i], int32(filters[i])
            )  # Setting the channel's filter

        # Clear previous trigger settings
        val = spcm_dwSetParam_i32(self.hCard, SPC_TRIG_ORMASK, SPC_TMASK_NONE)
        val1 = spcm_dwSetParam_i32(self.hCard, SPC_TRIG_ANDMASK, SPC_TMASK_NONE)
        if val != 0 or val1 != 0:
            print(f"Errors {val}, {val1} when setting trigger")

        # Setup the trigger
        if trigger:
            val = spcm_dwSetParam_i32(self.hCard, SPC_TRIG_ORMASK, SPC_TMASK_EXT0)
            if val != 0:
                print(f"Error {val} when setting trigger")

            # 0 value for all ensures ONLY external trigger used in OR mask.
            # can set so that output of channel 1 may be used as trigger for example
            val = spcm_dwSetParam_i32(self.hCard, SPC_TRIG_CH_ORMASK0, 0)
            val1 = spcm_dwSetParam_i32(self.hCard, SPC_TRIG_CH_ORMASK1, 0)
            val2 = spcm_dwSetParam_i32(self.hCard, SPC_TRIG_CH_ANDMASK0, 0)
            val3 = spcm_dwSetParam_i32(self.hCard, SPC_TRIG_CH_ANDMASK1, 0)
            if val != 0 or val1 != 0 or val2 != 0 or val3 != 0:
                print(f"Errors {val}, {val1}, {val2}, {val3} when setting trigger")

            # set mode and level of trigger
            val = spcm_dwSetParam_i32(self.hCard, SPC_TRIG_EXT0_MODE, SPC_TM_POS)
            val1 = spcm_dwSetParam_i32(
                self.hCard, SPC_TRIG_EXT0_LEVEL0, triggerLevel
            )  # in mV
            val2 = spcm_dwSetParam_i32(
                self.hCard, SPC_TRIG_TERM, 1
            )  # 50 Ohm termination
            val3 = spcm_dwSetParam_i64(self.hCard, SPC_TRIG_DELAY, 0)
            if val != 0 or val1 != 0 or val2 != 0 or val3 != 0:
                print(f"Errors {val}, {val1}, {val2}, {val3} when setting trigger")
            if self.verbose:
                print("Trigger mode set to external")

        else:
            val = spcm_dwSetParam_i32(self.hCard, SPC_TRIG_ORMASK, SPC_TMASK_SOFTWARE)
            if val != 0:
                print(f"Error {val} when setting trigger")
            if self.verbose:
                print("Trigger mode set to software")

        """

        Error might be here, setting the wrong memsize


        """
        self.llNumSamplesPerChannel = int(
            np.floor(self.numSamples / self.channelNum)
        )  # number of samples needed to represent the wave on one channel
        self.llNumSamplesPerChannel = int(
            self.llNumSamplesPerChannel + (32 - self.llNumSamplesPerChannel % 32)
        )  # round to 32 bit integer
        self.llLoops = int(loop)
        self.segSize = int(
            np.floor(self.numSamples / (self.numSegments * self.channelNum))
        )
        self.segmentSize = int(
            self.segSize + (16 - self.segSize % 16)
        )  # get the size of each segment (when applicable) and round to 16 bit integer

        # set the mode
        if sequenceReplay:
            val = spcm_dwSetParam_i32(self.hCard, SPC_CARDMODE, SPC_REP_STD_SEQUENCE)
            if self.verbose:
                print("Sequence Replay mode loaded w/ code : " + str(val))
            logsegments = int(
                np.ceil(math.log2(len(self.segTimes)))
            )  # we must divide memory into a power of 2 number of segments
            val1 = spcm_dwSetParam_i32(
                self.hCard, SPC_SEQMODE_MAXSEGMENTS, int32(2**logsegments)
            )
            val2 = spcm_dwSetParam_i32(
                self.hCard, SPC_SEQMODE_STARTSTEP, self.initialStep
            )  # specified step is the first step after you start the card
            if val1 != 0 or val2 != 0:
                print(
                    f"Initial sequenceReplay settings done with errors: {val1}, {val2}"
                )

        elif singleTrigger:
            val = spcm_dwSetParam_i32(self.hCard, SPC_CARDMODE, SPC_REP_STD_SINGLE)
            val1 = spcm_dwSetParam_i64(
                self.hCard, SPC_MEMSIZE, self.llNumSamplesPerChannel
            )
            val2 = spcm_dwSetParam_i64(self.hCard, SPC_LOOPS, self.llLoops)
            if val != 0 or val1 != 0 or val2 != 0:
                print(f"Errors {val}, {val1}, {val2} when setting mode")
            if self.verbose:
                print("Mode set to singleTrigger")

        elif singleRestart:
            val = spcm_dwSetParam_i32(
                self.hCard, SPC_CARDMODE, SPC_REP_STD_SINGLERESTART
            )
            val1 = spcm_dwSetParam_i64(
                self.hCard, SPC_MEMSIZE, self.llNumSamplesPerChannel
            )
            val2 = spcm_dwSetParam_i64(self.hCard, SPC_LOOPS, self.llLoops)
            if val != 0 or val1 != 0 or val2 != 0:
                print(f"Errors {val}, {val1}, {val2} when setting mode")
            if self.verbose:
                print("Mode set to singleRestart")

        elif multiTrigger:
            val = spcm_dwSetParam_i32(self.hCard, SPC_CARDMODE, SPC_REP_STD_MULTI)
            val1 = spcm_dwSetParam_i64(
                self.hCard, SPC_MEMSIZE, self.llNumSamplesPerChannel
            )
            val2 = spcm_dwSetParam_i64(self.hCard, SPC_SEGMENTSIZE, self.segmentSize)
            val3 = spcm_dwSetParam_i64(self.hCard, SPC_LOOPS, self.llLoops)
            if val != 0 or val1 != 0 or val2 != 0 or val3 != 0:
                print(f"Errors {val}, {val1}, {val2}, {val3} when setting mode")
            if self.verbose:
                print("Mode set to multiTrigger")

        elif extTrigger:
            val = spcm_dwSetParam_i32(self.hCard, SPC_CARDMODE, SPC_REP_STD_GATE)
            val1 = spcm_dwSetParam_i64(
                self.hCard, SPC_MEMSIZE, self.llNumSamplesPerChannel
            )
            val2 = spcm_dwSetParam_i64(self.hCard, SPC_LOOPS, self.llLoops)
            if val != 0 or val1 != 0 or val2 != 0:
                print(f"Errors {val}, {val1}, {val2} when setting mode")
            if self.verbose:
                print("Mode set to extTrigger")

    def changeAmplitude(self, amplitudes=[]):
        """
        Function to change the amplitude of the channels. Note that you must specify the amplitudes of all channels even if you are only changing one.
        """
        amplitudeList = [SPC_AMP0, SPC_AMP1, SPC_AMP2, SPC_AMP3]
        for i in range(0, self.channelNum, 1):
            spcm_dwSetParam_i32(self.hCard, amplitudeList[i], int32(amplitudes[i]))

    def checkCard(self):
        """
        Function that checks if the card used is indeed an M4i.6622-x8 or is compatible with Analog Output.
        """

        # Check if Card is connected
        if self.hCard == None:
            print("no card found...\n")
            return False

        # Getting the card Name to check if it's supported.
        try:
            sCardName = szTypeToName(self.lCardType.value)
            if self.lFncType.value == SPCM_TYPE_AO:
                print(
                    "Found: {0} sn {1:05d}\n".format(
                        sCardName, self.lSerialNumber.value
                    )
                )
                return True
            else:
                print(
                    "Code is for an M4i.6622 Card.\nCard: {0} sn {1:05d} is not supported.\n".format(
                        sCardName, lSerialNumber.value
                    )
                )
                return False

        except:
            dwError = spcm_dwSetParam_i32(
                self.hCard,
                SPC_M2CMD,
                M2CMD_CARD_START | M2CMD_CARD_ENABLETRIGGER | M2CMD_CARD_WAITREADY,
            )
            print(dwError)
            print("Problem !!! Card not loaded properly!")

    def setSoftwareBuffer(self):
        """
        Function to set up the SoftwareBuffer, no arguments required.
        """

        self.qwBufferSize = uint64(
            self.numSamples * self.lBytesPerSample.value
        )  # total size of the buffer

        # we try to use continuous memory if available and big enough
        self.pvBuffer = c_void_p()
        self.qwContBufLen = uint64(0)

    def setupCard(self, functionList, ttlFunctionList=[]):
        """
        Function that generates the data and transfers it to the card for all modes except sequenceReplay
        """
        if self.ttlOutOn:
            self.genBuffer(functionList, ttlFunctionList)
        else:
            self.genBuffer(functionList)
        self.transferData()
        return 0

    def getMaxDataLength(self):
        return self.numSamples

    def getSampleRate(self):
        return self.sampleRate

    def set_bit(self, n, p, b):
        """
        Sets the bit at position p of n to the value b=(1 or 0)
        """
        mask = 1 << p
        return (n & ~mask) | (b << p)

    def mix_ttl_and_analogue15(self, X, analogue_function, ttl_function):
        """WRITE DOCUMENTATION HERE IN A MINUTE"""
        # analogue = np.array(analogue_function(X)).astype(np.uint16)
        # shifted_down = (analogue >> 1) #& 0b0111111111111111 # Shift right 1 and clear highest bit to hold TTL signal
        # ttl_bit = np.array(ttl_function(X)).astype(np.uint16)
        #
        # for i in range(len(shifted_down)):
        #     shifted_down[i] = self.set_bit(shifted_down[i], 15, ttl_bit[i])
        #
        # return shifted_down #| (ttl_bit << 15)

        analogue = np.array(analogue_function(X)).astype(np.uint16)

        shifted_down = (
            analogue >> 1
        )  # & 0b0111111111111111 # Shift right 1 and clear highest bit to hold TTL signal
        ttl_bit = np.array(ttl_function(X)).astype(np.bool_)

        return np.int16(shifted_down | (ttl_bit << 15))

    def mix_ttl_and_analogue14(self, X, analogue_function, ttl_function):
        """WRITE DOCUMENTATION HERE IN A MINUTE"""
        # analogue = np.array(analogue_function(X)).astype(np.uint16)
        # shifted_down = (analogue >> 1) #& 0b0111111111111111 # Shift right 1 and clear highest bit to hold TTL signal
        # ttl_bit = np.array(ttl_function(X)).astype(np.uint16)
        #
        # for i in range(len(shifted_down)):
        #     shifted_down[i] = self.set_bit(shifted_down[i], 15, ttl_bit[i])
        #
        # return shifted_down #| (ttl_bit << 15)

        analogue = np.array(analogue_function(X)).astype(np.uint16)

        shifted_down = (
            analogue >> 1
        )  # & 0b0111111111111111 # Shift right 1 and clear highest bit to hold TTL signal
        ttl_bit_1 = np.array(ttl_function[1](X)).astype(np.bool_)

        data = np.uint16(shifted_down | (ttl_bit_1 << 15))

        shifted_down = data >> 1
        ttl_bit_2 = np.array(ttl_function[0](X)).astype(np.bool_)

        data = shifted_down | (ttl_bit_2 << 15)

        return np.int16(data)

    # def genBuffer(self, functionList):
    #     """
    #     Function that evaluates our functions at the proper domain values, producing the data for the waveforms.
    #     If segmented, functionList will be a list of lists [[CH1 Seg1, ..., CH1 SegN], [CH2 Seg1, ..., CH2 SegN]]
    #     """
    #     if self.singleTrigger or self.singleRestart or self.extTrigger:
    #         val = self.numSamples #how many samples we will need
    #         Y_vect = []
    #         functionNum = len(functionList)
    #         X = np.arange(0,(int)(val/self.channelNum),1) #creates the domain for each channel
    #
    #         for i in range(0,self.channelNum,1): #iterate through the channels
    #             if i > functionNum - 1:
    #                 """
    #                 If the channel number we are on in our iteration is greater than the length of our function list. For example, if we setup four channels but only
    #                 wish to use two. Then, channels 2 and 3 have their section of the data set to 0.
    #                 """
    #                 Y_vect = Y_vect + [np.zeros(len(X)).astype(int)]
    #             else:
    #                 Y_vect = Y_vect + [np.array(functionList[i](X)).astype(int)] #evaluate the function on our domain, producing a list of y-values represetnting the wave
    #
    #         self.buffer = np.column_stack(Y_vect).flatten()
    #         return 0
    #
    #     elif self.multiTrigger:
    #
    #         Y_vect = []
    #         val = self.segmentSize
    #         X = np.arange(0,(int)(val),1)
    #         for i in range(self.channelNum): #iterate through the channels
    #             for j in range(self.numSegments): #iterate through the segments for each channel
    #                 if i > len(functionList) - 1:
    #                     Y_vect = Y_vect + [np.zeros(len(X)).astype(int)]
    #                 else:
    #                     Y_vect = Y_vect + [(functionList[i][j](X)).astype(int)] #find the correct function and evaluate at our domain
    #
    #
    #         self.buffer = [item for sublist in Y_vect for item in sublist]
    #         k = 0
    #         self.parsed_data = []
    #
    #         while k < self.numSegments*self.segmentSize:
    #             for i in range(self.channelNum):
    #                 self.parsed_data.append(self.buffer[k + (i*self.segmentSize*self.numSegments)])
    #             k += 1

    def genBuffer(self, functionList, ttlFunctionList=[]):
        """
        Function that evaluates our functions at the proper domain values, producing the data for the waveforms.
        If segmented, functionList will be a list of lists [[CH1 Seg1, ..., CH1 SegN], [CH2 Seg1, ..., CH2 SegN]]
        """

        if self.singleTrigger or self.singleRestart or self.extTrigger:
            val = self.numSamples  # how many samples we will need
            Y_vect = []
            functionNum = len(functionList)
            X = np.arange(
                0, (int)(val / self.channelNum), 1
            )  # creates the domain for each channel
            for i in range(0, self.channelNum, 1):  # iterate through the channels
                if i > functionNum - 1:
                    """
                    If the channel number we are on in our iteration is greater than the length of our function list. For example, if we setup four channels but only
                    wish to use two. Then, channels 2 and 3 have their section of the data set to 0.
                    """
                    Y_vect = Y_vect + [np.zeros(len(X)).astype(int)]
                else:
                    if self.ttlOutOn and i == self.ttlSourceChannel:
                        if len(self.ttlOutChannel) == 1:
                            Y_vect = Y_vect + [
                                self.mix_ttl_and_analogue15(
                                    X, functionList[i], ttlFunctionList[i]
                                )
                            ]
                        elif len(self.ttlOutChannel) == 2:
                            Y_vect = Y_vect + [
                                self.mix_ttl_and_analogue14(
                                    X, functionList[i], ttlFunctionList[i]
                                )
                            ]

                    else:
                        Y_vect = Y_vect + [
                            np.array(functionList[i](X)).astype(int)
                        ]  # evaluate the function on our domain, producing a list of y-values represetnting the wave

            self.buffer = np.column_stack(Y_vect).flatten()
            return 0

        elif self.multiTrigger:
            Y_vect = []
            val = self.segmentSize
            X = np.arange(0, (int)(val), 1)
            for i in range(self.channelNum):  # iterate through the channels
                for j in range(
                    self.numSegments
                ):  # iterate through the segments for each channel
                    if i > len(functionList) - 1:
                        Y_vect = Y_vect + [np.zeros(len(X)).astype(int)]
                    else:
                        if self.ttlOutOn and j == self.ttlSourceChannel:
                            if len(self.ttlOutChannel) == 1:
                                Y_vect = Y_vect + [
                                    self.mix_ttl_and_analogue15(
                                        X, functionList[i], ttlFunctionList[i]
                                    )
                                ]
                            elif len(self.ttlOutChannel) == 2:
                                Y_vect = Y_vect + [
                                    self.mix_ttl_and_analogue14(
                                        X, functionList[i], ttlFunctionList[i]
                                    )
                                ]
                        else:
                            Y_vect = Y_vect + [
                                np.array(functionList[i](X)).astype(int)
                            ]  # evaluate the function on our domain, producing a list of y-values represetnting the wave

            self.buffer = [item for sublist in Y_vect for item in sublist]
            k = 0
            self.parsed_data = []

            while k < self.numSegments * self.segmentSize:
                for i in range(self.channelNum):
                    self.parsed_data.append(
                        self.buffer[k + (i * self.segmentSize * self.numSegments)]
                    )
                k += 1

    def programTTLOut(self):
        if self.ttlSourceChannel == 0:
            spcm_ttl_source_code = SPCM_XMODE_DIGOUTSRC_CH0
        elif self.ttlSourceChannel == 1:
            spcm_ttl_source_code = SPCM_XMODE_DIGOUTSRC_CH1
        elif self.ttlSourceChannel == 2:
            spcm_ttl_source_code = SPCM_XMODE_DIGOUTSRC_CH2
        elif self.ttlSourceChannel == 3:
            spcm_ttl_source_code = SPCM_XMODE_DIGOUTSRC_CH3

        if len(self.ttlOutChannel) == 2:
            dwXMode = (
                SPCM_XMODE_DIGOUT | spcm_ttl_source_code | SPCM_XMODE_DIGOUTSRC_BIT15
            )
            val = spcm_dwSetParam_i32(
                self.hCard, SPCM_X0_MODE + self.ttlOutChannel[0], uint32(dwXMode)
            )
            # if self.verbose:
            print(
                f"TTL out enabled w/ code : {str(val)}. Bit 15 of channel {self.ttlOutChannel} is now used for TTL out."
            )

            dwXMode = (
                SPCM_XMODE_DIGOUT | spcm_ttl_source_code | SPCM_XMODE_DIGOUTSRC_BIT14
            )
            val = spcm_dwSetParam_i32(
                self.hCard, SPCM_X0_MODE + self.ttlOutChannel[1], uint32(dwXMode)
            )
            print(
                f"TTL out enabled w/ code : {str(val)}. Bit 14 of channel {self.ttlOutChannel} is now used for TTL out."
            )

        else:
            dwXMode = (
                SPCM_XMODE_DIGOUT | spcm_ttl_source_code | SPCM_XMODE_DIGOUTSRC_BIT15
            )
            val = spcm_dwSetParam_i32(
                self.hCard, SPCM_X0_MODE + self.ttlOutChannel[0], uint32(dwXMode)
            )
            # val = spcm_dwSetParam_i32 (self.hCard, SPCM_X0_MODE + self.ttlOutChannel, SPCM_XMODE_RUNSTATE)
            # if self.verbose:
            print(
                f"TTL out enabled w/ code : {str(val)}. Bit 15 of channel {self.ttlOutChannel} is now used for TTL out."
            )

    def transferData(self):
        try:
            self.pvBuffer = np.zeros(self.qwBufferSize.value, dtype="uint16")  # uint16
            if self.multiTrigger:
                self.pvBuffer[0 : len(self.parsed_data)] = np.array(self.parsed_data)
            else:
                self.pvBuffer[0 : len(self.buffer)] = np.array(self.buffer)

            self.trueBuffer = self.pvBuffer.tobytes()  # the data to bytes

            # Define the buffer for transfer and start the DMA transfer
            if self.verbose:
                print(
                    "Starting the DMA transfer and waiting until data is in board memory\n"
                )
            val = spcm_dwDefTransfer_i64(
                self.hCard,
                SPCM_BUF_DATA,
                SPCM_DIR_PCTOCARD,
                uint32(self.qwBufferSize.value),
                self.trueBuffer,
                uint64(0),
                self.qwBufferSize,
            )
            if val != 0:
                print(f"Error in data transfer, error code {val}\n")
            if self.verbose:
                print("Finished initial transfer\n")
            val = spcm_dwSetParam_i32(
                self.hCard, SPC_DATA_AVAIL_CARD_LEN, self.qwBufferSize
            )
            if val != 0:
                print(f"Error in data transfer, error code {val}\n")
            # after filling an amount of the buffer with new data to transfer to card, this tells the register that the amount of data is ready to transfer
            if self.verbose:
                print("Got full data size\n")
            val = spcm_dwSetParam_i32(
                self.hCard, SPC_M2CMD, M2CMD_DATA_STARTDMA | M2CMD_DATA_WAITDMA
            )  # transfer the data and wait for it to be done before returning
            if val != 0:
                print(f"Error in data transfer, error code {val}\n")
            if self.verbose:
                print("... data has been transferred to board memory\n")

            return 0

        except KeyboardInterrupt:
            print("Broken Operation\n")
            return -1
            exit()

    def configSequenceReplay(self, segFunctions=[], steps=[], ttlFunctionList=[]):
        # configuring memory segments
        self.segFunctions = segFunctions
        self.steps = steps

        for i in range(len(segFunctions)):  # iterate through the segments
            size = (
                self.segTimes[i] * self.sampleRate
            )  # gets the number of data points we need to represent this segment
            size = int(size + (32 - size % 32))  # round into allowable value
            # print(f"Size for segment {i} is {size}")
            Y_vect = []
            X = np.arange(0, (int)(size), 1)

            for j in range(
                self.channelNum
            ):  # iterate through the channels for each segment
                if (
                    j > len(self.segFunctions[i]) - 1
                ):  # if we set up more channels than we're using, fill them with 0s
                    Y_vect = Y_vect + [np.zeros(len(X)).astype(int)]
                else:
                    # Y_vect = Y_vect + [np.array(self.segFunctions[i][j](X)).astype(int)] #the data, for the ith segment take the ith function and evaluate
                    if self.ttlOutOn and j == self.ttlSourceChannel:
                        if len(self.ttlOutChannel) == 1:
                            Y_vect = Y_vect + [
                                self.mix_ttl_and_analogue15(
                                    X, self.segFunctions[i][j], ttlFunctionList[i]
                                )
                            ]
                        elif len(self.ttlOutChannel) == 2:
                            Y_vect = Y_vect + [
                                self.mix_ttl_and_analogue14(
                                    X, self.segFunctions[i][j], ttlFunctionList[i]
                                )
                            ]
                    else:
                        Y_vect = Y_vect + [
                            np.array(self.segFunctions[i][j](X)).astype(int)
                        ]  # evaluate the function on our domain, producing a list of y-values representing the wave

            self.buffer = np.column_stack(Y_vect).flatten()
            # print(f"For iteration {i}, data is {self.buffer}")

            self.pvBuffer = np.zeros(self.qwBufferSize.value, dtype="uint16")
            self.pvBuffer[0 : len(self.buffer)] = np.array(self.buffer)
            self.trueBuffer = self.pvBuffer.tobytes()  # the data to bytes

            val = spcm_dwSetParam_i32(
                self.hCard, SPC_SEQMODE_WRITESEGMENT, i
            )  # specifies that we are writing the ith segment
            if val != 0:
                print(f"Error in SPC_SEQMODE_WRITESEGMENT, code {val} for segment {i}")

            val = spcm_dwSetParam_i32(
                self.hCard, SPC_SEQMODE_SEGMENTSIZE, size
            )  # writes the size of the segment
            if val != 0:
                print(f"Error in SPC_SEQMODE_SEGMENTSIZE, code {val} for segment {i}")

            # transfer the data for this segment
            val = spcm_dwDefTransfer_i64(
                self.hCard,
                SPCM_BUF_DATA,
                SPCM_DIR_PCTOCARD,
                0,
                self.trueBuffer,
                0,
                (int)(size * self.lBytesPerSample.value * self.channelNum),
            )
            if val != 0:
                print(f"Error in spcm_dwDefTransfer_i64, code {val} for segment {i}")
            val = spcm_dwSetParam_i32(
                self.hCard, SPC_M2CMD, M2CMD_DATA_STARTDMA | M2CMD_DATA_WAITDMA
            )
            if val != 0:
                print(f"Error in spcm_dwSetParam_i32, code {val} for segment {i}")

        # configuring sequence steps
        for i in range(len(steps)):
            if i == 0:  # which segment to play for this step
                llSegment = self.initialStep
            else:
                llSegment = llNext

            llSegment = self.steps[i]
            llLoop = self.loop_list[i]  # how many times to loop this segment
            llNext = self.next[i]  # what segment to go to next
            llCondition = self.conditions[
                i
            ]  # condition telling us when to go to this next segment

            llValue = (
                (llCondition << 32) | (llLoop << 32) | (llNext << 16) | (llSegment)
            )  # puts all of these parameters into one int64 bit value

            # the line below is useful for debugging but will clutter your screen during normal use
            # print(f"Step params are, condition = {llCondition}, loops = {llLoop}, next = {llNext}, segment = {llSegment}, value = {llValue} for step {i}")

            val = spcm_dwSetParam_i64(
                self.hCard, SPC_SEQMODE_STEPMEM0 + i, int64(llValue)
            )  # writes the parameters for the ith step in our sequence
            if val != 0:
                print(
                    f"Error in setting the sequence with code {val} for iteration {i}"
                )

    def startCard(self, checkClock=True):
        try:
            spcm_dwSetParam_i32(self.hCard, SPC_TIMEOUT, 0)
            dwError = spcm_dwSetParam_i32(
                self.hCard, SPC_M2CMD, M2CMD_CARD_START | M2CMD_CARD_ENABLETRIGGER
            )

            if dwError == ERR_CLOCKNOTLOCKED:
                # If an external clock is being used, there is a chance the PLL
                # hasn't locked to the clock signal properly, either because it
                # is unstable or because the signal levels are not in range.
                # This error will appear when starting the card and so is
                # checked here.
                print("ERROR: External clock not locked. Please check connection.\n")
            else:
                if dwError != 0:
                    print(f"Error when starting card with code {dwError}")

            if checkClock:
                val = int32(0)
                spcm_dwGetParam_i32(self.hCard, SPC_CLOCKMODE, byref(val))
                if val.value == SPC_CM_EXTREFCLOCK:
                    print("External clock locked.")
                else:
                    print("ERROR: External clock not locked. Please check connection.")
                    print(val.value)

            print("Starting the card\n")

        except KeyboardInterrupt:
            print("Process finished.")

            return -1

    def stop(self):
        """
        Command to stop the Card. To use card again, need to reinitialize
        """
        # send the stop command
        try:
            dwError = spcm_dwSetParam_i32(
                self.hCard, SPC_M2CMD, M2CMD_CARD_STOP | M2CMD_DATA_STOPDMA
            )
            print("Card has been Stopped")
            if dwError != 0:
                print(f"Error when stopping card with code {dwError}")
            spcm_vClose(self.hCard)
            return 0
        except Exception as e:
            print("Exception", str(e), " has occured")
            return -1

    def stopWithoutClosing(
        self,
    ):  # This worked on one simple test. Need to make sure it reliably works as it is known to be faulty.
        """
        Command to stop the Card. To use card again, need to reinitialize
        """
        # send the stop command
        try:
            dwError = spcm_dwSetParam_i32(
                self.hCard, SPC_M2CMD, M2CMD_CARD_STOP | M2CMD_DATA_STOPDMA
            )
            # print(dwError)
            print("Card has been Stopped")
            return 0
        except Exception as e:
            print("Exception", str(e), " has occured")
            return -1
