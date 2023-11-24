"""
PCIE Digitizer Header file

All voltages values are in volts and amplitudes, not peak to peak. 
The +- 1V setting for acquisition does not work. 
Changes to make, not critical:
 - do not load the .ini file and then overwrite the parameters you want to change. Just set up your own dictionary full of the defaul values of every parameter
 
Last Updated by: Alek Radak
Last Update: 11/22/23
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
        
        self.verbose = verbose

        """ Initialize the Digitizer and connect to it"""
        if self._handle < 0:
            # get error string
            error_string = PyGage.GetErrorString(self._handle)
            print("Error: ", error_string, "\n")
            raise SystemExit

        """ Get the info to make sure everything is working """
        self._system_info = PyGage.GetSystemInfo(self._handle)
        if not isinstance(
            self._system_info, dict
        ):  # if it's not a dict, it's an int indicating an error
            print("Error: ", PyGage.GetErrorString(self._system_info), "\n")
            PyGage.FreeSystem(self._handle)
            raise SystemExit

        if self.verbose:
            print("\nBoard Name: ", self._system_info["BoardName"], "\n")

    def initialize(self):
        """Connect and initialize the digitizer"""
        status = PyGage.Initialize()
        if status < 0:
            return status
        else:
            handle = PyGage.GetSystem(0, 0, 0, 0)
            return handle

    def test_verbose(self):
        if self.verbose:
            print('verbose is true')
    

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
        trigger_timeout: int = -1,
        voltage_range: Literal[0.1, 0.2, 0.5, 2, 5] = 2,
        ):
        """Configure the acquisition and trigger parameters of the digitizer

        Parameters:
            - mode: 1 for single channel, 2 for dual channel.
            - sample_rate: integer for the sample rate. Must be in [100MS/s, 65MS/s, 50MS/s, 40MS/s, 25MS/s, 20MS/s, 10MS/s, 5MS/s, 2MS/s, 1MS/s]
            - segment_size: The amount of samples taken per segment after the digitizer has been triggered.
            - segment_count: The total number of segments the digitizer expects.
            - trigger_holdoff: number of samples after a trigger before digitizer can be triggered again.
            - voltage_range: voltage range in volts. This specifies the max AMPLITUDE of the input voltage, not peak to peak. Allowed values are [0.1,0.2,0.5,2,5] with default 2 for whatever reason 1 doesnt work :/
            - trigger_timeout: how long to wait before the software forces a trigger event, in units of 100ns, default is -1 which means wait indefinitely

        The other parameters can be changed by looking at the default parameters file at the filename location
        This method can be run multiple times to change the configuration of the digitizer before starting acquisition.

        This filename is dependent on where you store the file, create your own if you're using this header file and put the path here.
        """
        self.mode = mode
        self.sample_rate = sample_rate
        self.segment_count = segment_count
        self.trigger_holdoff = trigger_holdoff
        self.voltage_range = voltage_range
        self.segment_size = segment_size

        filename = "/home/onix/Documents/code/onix/headers/pcie_digitizer/digitizerParameters.ini"

        acq, sts = gs.LoadAcquisitionConfiguration(self._handle, filename)

        if segment_size is not None:
            overflow = segment_size % 16
            if overflow > 0:
                segment_size = segment_size + 16 - overflow
                self.overflow = 16 - overflow
            else:
                self.overflow = 0

            self.segment_size = segment_size

        if self.mode == 1 or self.mode == 2:
            acq["Mode"] = self.mode
        else:
            acq['Mode'] = 2
            print('Invalid Mode. Setting to 2\n')
            
            
        """ Setting parameters if they've been changed manually """
        
        possible_sample_rates = [100000000,65000000, 50000000, 40000000, 25000000,20000000,10000000,5000000,2000000,1000000]
        
        if self.sample_rate in possible_sample_rates :
            acq["SampleRate"] = self.sample_rate
        else:
            print('Invalid sample rate. Using 100MS/s \n')
            acq["SampleRate"] = 100000000
        
        if self.segment_size is not None:
            if isinstance(self.segment_size, int):
                acq["SegmentSize"] = self.segment_size
                acq["Depth"] = self.segment_size
            else:
                print('Invalid segment size. Using 4000 \n')
                acq["SegmentSize"] = 4000
                acq["Depth"] = 4000
        else:
            acq["SegmentSize"] = 4000
            acq["Depth"] = 4000
            if self.verbose:
                print('Using default segment size 4000 \n')
            
        
        if self.segment_count is not None:
            if isinstance(self.segment_count, int):
                acq["SegmentCount"] = self.segment_count
            else:   
                print('Invalid segment count. Setting to 1 \n')
                acq["SegmentCount"] = 1
        else:
            acq["SegmentCount"] = 1
            if self.verbose:
                print('Using default segment count 1 \n')
            
                
               
        if isinstance(self.trigger_holdoff,int):
            acq["TriggerHoldoff"] = self.trigger_holdoff
        else:
            print('Invalid trigger holdoff. Using 0 \n')
            acq["TriggerHoldoff"] = 0
        
            
        

        if isinstance(trigger_timeout, int):
            acq['TriggerTimeout'] = trigger_timeout
        else:
            print('Invalid trigger timeout. Using -1 \n')
            acq['TriggerTimeout'] = -1

                

        self._acq = acq
        self._sts = sts

        """ Code gotten from GaGe Python header. Checks that the input parameters are correct and configured the digitizer """
        if isinstance(acq, dict) and acq:
            status = PyGage.SetAcquisitionConfig(self._handle, acq)
            if status < 0:
                print("Invalid Parameters! Check you've input the correct dictonary \n")
                return status
        else:
            print("Using defaults for acquisition parameters \n")

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
            voltage_ranges = [0.1, 0.2, 0.5, 2, 5]
            if voltage_range in voltage_ranges:
                chan["InputRange"] = int(2*1000*voltage_range)
            else:
                print(f'Invalid voltage range on channel {i}. Using +- 2V \n')
                voltage_range = 2
                chan["InputRange"] = int(2*1000*voltage_range)
           
            self._chan.append(chan)
            if isinstance(chan, dict) and chan:
                status = PyGage.SetChannelConfig(self._handle, i, chan)
                if status < 0:
                    return status
            else:
                print("Using default parameters for channel ", i, "\n")

            if sts == gs.PARAMETERS_MISSING:
                missing_parameters = True

            self._chan.append(chan)

        if missing_parameters:
            print(
                "One or more channel parameters missing, using defaults for missing values \n"
            )

        missing_parameters = False

        status = PyGage.Commit(self._handle)

        self._system_info = PyGage.GetSystemInfo(self._handle)
        error_string = PyGage.GetErrorString(status)
        return error_string


    def configure_trigger(
        self,
        source: Literal["external", "software", None] = "external",
        edge: Literal["rising", "falling", None] = "rising",
        trigger_range: Union[int, None] = 5,
        level: Union[int, None] = 30,
        impedance: Literal[50,1000000, None] = 50,
        coupling: Literal['AC', 'DC', None] = 'DC',
        ):

        """
        Configure the trigger.

        Parameters:
        - source: External or software. If software, the trigger event will occur after 100ns. Defaults to external. 
        - edge: rising or falling, defaults to rising
        - trigger_range: amplitude of input, in Volts, defaults to +- 5V input
        - level: percentage of input range at which to trigger, defaults to 30%
        - impedance: 50Ohm or 1MOhm, defaults to 1MOhm
        - coupling: AC or DC, defaults to DC

        Example: to external trigger
        dg = Digitizer()
        val = dg.configure_system(...)
        val = dg.configure_trigger(
            source = 'external',
            edge = 'falling',
            trigger_range = 3,
            level = 40,
            impedance = 50,
            coupling = 'DC'
            )
            
        Example: to software trigger
        dg = Digitizer()
        val = dg.configure_system(...)
        val = dg.configure_trigger(source = 'software')
        """

        filename = "/home/onix/Documents/code/onix/headers/pcie_digitizer/digitizerParameters.ini"
        trig, sts = gs.LoadTriggerConfiguration(self._handle, 1, filename)

        if source is not None:
            if source == 'software':
                trig['Source'] = 0
                self.configure_system(
                    mode = self.mode,
                    sample_rate = self.sample_rate,
                    segment_size = self.segment_size,
                    segment_count = self.segment_count,
                    trigger_holdoff = self.trigger_holdoff,
                    trigger_timeout = 1,
                    voltage_range = self.voltage_range)
                    #reconfigure the system using the exact same setting, force software trigger after 100ns
            elif source == "external":
                trig['Source'] = -1
            else:
                print("Invalid trigger source. Using default external. \n")
                trig['Source'] = -1
        else:
            trig['Source'] = -1
            if self.verbose:
                print('Using default trigger source external \n')
                


        if edge == "rising":
            trig['Condition'] = 1
        elif edge == "falling":
            trig['Condition'] = 0
        else:
            print('Invalid trigger edge setting. Using default rising \n')
            trig['Condition'] = 1
 
                
          

        if isinstance(trigger_range,int):
            trig['ExtRange'] = int(2*1000*trigger_range)   
        else:
            print('Invalid trigger_range. Using default +- 5V \n')
            trig['ExtRange'] = int(2*1000*5)
                

        if isinstance(level, int):
            trig['Level'] = level
        else:
            print('Invalid trigger level. Using default 30% \n')
            trig['Level'] = 30

            

        if impedance == 50 or impedance == 1000000:
            trig['ExtImpedance'] = impedance
        else:
            print('Invalid impedance. Using default 50 Ohm \n') 
            trig['ExtImpedance'] = 50


        if coupling == 'AC':
            trig['ExtCoupling'] = 2
        elif coupling == 'DC':
            trig['ExtCoupling'] = 1
        else:
            print('Invalid couping. Using default DC. \n')
            trig['ExtCoupling'] = 1


        missing_parameters = False

        if isinstance(trig, dict) and trig:
            status = PyGage.SetTriggerConfig(self._handle, 1, trig)
            if status < 0:
                return status
        else:
            print("Using default parameters for trigger ", status, "\n")

        if sts == gs.PARAMETERS_MISSING:
            missing_parameters = True

        if missing_parameters:
            print("One or more trigger parameters missing, using defaults for missing values \n")


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
            print("Error getting acquisition parameters. Code: ", e, "\n")

    def get_channel_parameters(self, chan: Literal[1, 2]):
        """return the current channel parameters of the digitizer, if they're available"""
        try:
            return PyGage.GetChannelConfig(self._handle, chan)
        except Exception as e:
            print("Error getting channel parameters. Code: ", e, "\n")

    def get_trigger_parameters(self):
        try:
            return PyGage.GetTriggerConfig(self._handle, 1)
        except Exception as e:
            print("Error getting trigger parameters. Code: ", e, "\n")

    def arm_digitizer(self):
        status = PyGage.StartCapture(self._handle)
        if status < 0:
            return status

    def get_data(self):
        """Returns the digitizer data in 3-dim np.array.
        
        The first dimension iterates over all channels.
        The second dimension iterates over all segments.
        The third dimension stores data in each segment.
        """
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

        return np.array(channel_data)

    def close(self):
        PyGage.FreeSystem(self._handle)
