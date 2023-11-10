"""
PCIE Digitizer Header file,


Everything working. Enables you do set the aquisition parameters and the trigger parameters.
The only thing not working is the +-1V setting for the aquisition system, for whatever reason there is an extra factor of 2 added to everything

Last Updated by: Daniel Stedman
Last Update: 10/19/23

Changed needed:
  * Enable setting external or software triggering using this header file. (solved)
  * Code snippets to show how to take data with external and internal triggers. (solved)
  * Read correct voltages. Currently the voltages read are not correct.
  * Investigate crash issues when the digitizer takes data multiple times, or takes a lot of data. (solved)
  * It does not return the number of samples set exactly. (solved)
"""
import os
import sys
from builtins import int
import platform
import sys
import pathlib
from typing import List, Literal, Tuple, Union
from datetime import datetime
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


class Digitizer:

    """
    Digitizer class, used to operate the GaGe CSE8327 Octave Express Digitizer.

    This header file allows the digitizer to be initialized in python.


    Parameters:
     - verbose: Allow print statements that are not error mesasges.


    When running dg.configure_system, you are able to set the number of channels, sample rate, number of segments, segment size, trigger holdoff
    To change more settings you must change the parameters in the digitizerParameters file stored in the same location as the header code.
    The parameters in the file allow to you configure many other elements of the digitizer, for more information see the INI_FILE_DESCRIPTION.pdf.

    To change specific parameters, you can call dg.configure_parameter( ... ) where the parameter is a dictionary of the parameters you wish to change and their values.

    """

    def __init__(self, verbose: bool = False):
        self._handle = self.initialize()
        self.overflow = 0

        """ Initialize the Digitizer and connect to it"""
        if self._handle < 0:
            # get error string
            error_string = PyGage.GetErrorString(self._handle)
            print("Error: ", error_string)
            raise SystemExit

        """ Get the info to make sure everything is working """
        self._system_info = PyGage.GetSystemInfo(self._handle)
        if not isinstance(
            self._system_info, dict
        ):  # if it's not a dict, it's an int indicating an error
            print("Error: ", PyGage.GetErrorString(self._system_info))
            PyGage.FreeSystem(self._handle)
            raise SystemExit

        if verbose:
            print("\nBoard Name: ", self._system_info["BoardName"])

    def initialize(self):
        """Connect and initialize the digitizer"""
        status = PyGage.Initialize()
        if status < 0:
            return status
        else:
            handle = PyGage.GetSystem(0, 0, 0, 0)
            return handle

    def configure_system(
        self,
        mode: Literal[1, 2],
        sample_rate: Literal[
            100000000,
            65000000,
            50000000,
            40000000,
            25000000,
            20000000,
            10000000,
            5000000,
            2000000,
            1000000,
        ] = 100000000,
        segment_size: Union[int, None] = None,
        segment_count: Union[int, None] = None,
        trigger_holdoff: int = 0,
        voltage_range: Literal[100, 200, 500, 2000, 5000] = 2000,):
        """Configure the acquisition and trigger parameters of the digitizer

        Parameters:
            - mode: 1 for single channel, 2 for dual channel.
            - sample_rate: integer for the sample rate. Must be in [100MS/s, 65MS/s, 50MS/s, 40MS/s, 25MS/s, 20MS/s, 10MS/s, 5MS/s, 2MS/s, 1MS/s]
            - segment_size: The amount of samples taken per segment after the digitizer has been triggered.
            - segment_count: The total number of segments the digitizer expects.
            - trigger_holdoff: number of samples after a trigger before digitizer can be triggered again.
            - voltage_range: voltage range in volts. This specifies the max AMPLITUDE of the input voltage, not peak to peak. Allowed values are [100,200,500,2000,5000] for whatever reason 1000 doesnt work :/

        The other parameters can be changed by looking at the default parameters file at the filename location
        This method can be run multiple times to change the configuration of the digitizer before starting acquisition.

        This filename is dependent on where you store the file, create your own if you're using this header file and put the path here.
        """

        filename = "/home/onix/Documents/code/onix/headers/pcie_digitizer/digitizerParameters.ini"

        acq, sts = gs.LoadAcquisitionConfiguration(self._handle, filename)

        overflow = segment_size % 16
        if overflow > 0:
            segment_size = segment_size + 16 - overflow
            self.overflow = 16 - overflow
        else:
            self.overflow = 0

        acq["Mode"] = mode

        """ Setting parameters if they've been changed manually """
        if sample_rate is not None:
            acq["SampleRate"] = sample_rate
        if segment_size is not None:
            acq["SegmentSize"] = segment_size
        if segment_size is not None:
            acq["Depth"] = segment_size
        if segment_count is not None:
            acq["SegmentCount"] = segment_count
        acq["TriggerHoldoff"] = trigger_holdoff

        self._acq = acq
        self._sts = sts

        """ Code gotten from GaGe Python header. Checks that the input parameters are correct and configured the digitizer """
        if isinstance(acq, dict) and acq:
            status = PyGage.SetAcquisitionConfig(self._handle, acq)
            if status < 0:
                print("Invalid Parameters! Check you've input the correct dictonary")
                return status
        else:
            print("Using defaults for acquisition parameters")

        if sts == gs.INI_FILE_MISSING:
            print("Missing ini file, using defaults")
        elif sts == gs.PARAMETERS_MISSING:
            print(
                "One or more acquisition parameters missing, using defaults for missing values"
            )

        self._system_info = PyGage.GetSystemInfo(self._handle)
        self._acq = PyGage.GetAcquisitionConfig(self._handle)

        channel_increment = gs.CalculateChannelIndexIncrement(
            acq["Mode"],
            self._system_info["ChannelCount"],
            self._system_info["BoardCount"],
        )

        self._chan = []

        missing_parameters = False
        for i in range(1, self._system_info["ChannelCount"] + 1, channel_increment):
            chan, sts = gs.LoadChannelConfiguration(self._handle, i, filename)
            chan["InputRange"] = int(2*voltage_range)
            self._chan.append(chan)
            if isinstance(chan, dict) and chan:
                status = PyGage.SetChannelConfig(self._handle, i, chan)
                if status < 0:
                    return status
            else:
                print("Using default parameters for channel ", i)

            if sts == gs.PARAMETERS_MISSING:
                missing_parameters = True

            self._chan.append(chan)

        if missing_parameters:
            print(
                "One or more channel parameters missing, using defaults for missing values"
            )

        missing_parameters = False

        status = PyGage.Commit(self._handle)

        self._system_info = PyGage.GetSystemInfo(self._handle)
        error_string = PyGage.GetErrorString(status)
        return error_string


    def configure_trigger(
        self,
        edge: Literal["rising", "falling"] = "rising",
        level: int = 30,
        source: Literal["external", "software"] = "external",
        range: int = 10000,
        impedance: Literal[50,1000000] = 1000000,
        coupling: Literal['AC', 'DC'] = 'DC',
        ):

        """
        Configure the trigger.

        Parameters:
        - edge: rising or falling
        - level: trigger level as a percent of input range
        - source: external or internal
        - range: maximum trigger voltage in volts
        - impedance: 50 Ohm or 1 MOhm

        Example: to external trigger
        dg = Digitizer()
        val = dg.configure_system(...)
        val = dg.configure_trigger(
            edge = 'falling',
            level = 40,
            source = 'external',
            range = 3,
            impedance = 50,
            coupling = 'DC'
            )

        To set software trigger, set source = 'software'. All other params will be ignored if on software trigger.
        """

        filename = "/home/onix/Documents/code/onix/headers/pcie_digitizer/digitizerParameters.ini"
        trig, sts = gs.LoadTriggerConfiguration(self._handle, 1, filename)


        if edge == "rising":
            trig['Condition'] = 1
        elif edge == "falling":
            trig['Condition'] = 0

        if level is not None:
            trig['Level'] = level

        if source == 'software':
            trig['Source'] = 0
        elif source == "external":
            trig['Source'] = -1

        if range is not None:
            trig['ExtRange'] = int(range)

        if impedance is not None:
            trig['ExtImpedance'] = impedance

        if coupling == 'AC':
            trig['ExtCoupling'] = 2
        elif coupling == 'DC':
            trig['ExtCoupling'] = 1


        missing_parameters = False

        if isinstance(trig, dict) and trig:
            status = PyGage.SetTriggerConfig(self._handle, 1, trig)
            if status < 0:
                return status
        else:
            print("Using default parameters for trigger ", status)

        if sts == gs.PARAMETERS_MISSING:
            missing_parameters = True

        if missing_parameters:
            print(
                "One or more trigger parameters missing, using defaults for missing values"
            )


        self._trig = trig

        status = PyGage.Commit(self._handle)

        self._system_info = PyGage.GetSystemInfo(self._handle)
        error_string = PyGage.GetErrorString(status)
        return error_string

    def get_acquisition_parameters(self):
        """return the current aquisition parameters of the digitizer, if they're available"""
        try:
            return PyGage.GetAcquisitionConfig(self._handle)
        except Exception as e:
            print("Error getting acquisition parameters. Code: ", e)

    def get_channel_parameters(self, chan: Literal[1, 2]):
        """return the current channel parameters of the digitizer, if they're available"""
        try:
            return PyGage.GetChannelConfig(self._handle, chan)
        except Exception as e:
            print("Error getting channel parameters. Code: ", e)

    def get_trigger_parameters(self):
        try:
            return PyGage.GetTriggerConfig(self._handle, 1)
        except Exception as e:
            print("Error getting trigger parameters. Code: ", e)

    def arm_digitizer(self):
        status = PyGage.StartCapture(self._handle)
        if status < 0:
            return status

    def get_data(self):
        filename = "/home/onix/Documents/code/onix/headers/pcie_digitizer/digitizerParameters.ini"

        mode = PyGage.GetAcquisitionConfig(self._handle)["Mode"]
        app, sts = gs.LoadApplicationConfiguration(filename)

        channel_increment = gs.CalculateChannelIndexIncrement(
            mode, self._system_info["ChannelCount"], self._system_info["BoardCount"]
        )

        acq = PyGage.GetAcquisitionConfig(self._handle)

        min_start_address = acq["TriggerDelay"] + acq["Depth"] - acq["SegmentSize"]
        if app["StartPosition"] < min_start_address:
            print(
                "\nInvalid Start Address was changed from {0} to {1}".format(
                    app["StartPosition"], min_start_address
                )
            )
            app["StartPosition"] = min_start_address

        channel_data = []

        for i in range(1, self._system_info["ChannelCount"] + 1, channel_increment):
            segment_data = []
            for group in range(1, acq["SegmentCount"] + 1):
                data = PyGage.TransferData(
                    self._handle, i, gc.TxMODE_DEFAULT, group, 0, acq["Depth"]
                )

                if isinstance(data, int):
                    print(f"Data tranfer error! {data}")
                    return []

                data = np.array(data[0])

                data = data[0 : acq["Depth"] - self.overflow]

                data = (data / 2**16) * (self._chan[i]['InputRange'] * 1e-3)

                segment_data.append(data)

            segment_data = np.array(segment_data)

            channel_data.append(segment_data)

        #PyGage.FreeSystem(self._handle)

        return np.array(channel_data)





