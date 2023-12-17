"""
PCIE Digitizer Header file

All voltages values are in volts and amplitudes, not peak to peak. 
The +- 1V setting for acquisition does not work. 
If you set the trigger level too low (below 10%) sometimes it will work, sometimes it will throw an error.


Problem: it crashes when we initialize the header object many times in an experiment.
 
Last Updated by: Alek Radak
Last Update: 11/28/23
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



"""
Setting the defualt parameters for all of the settings
"""

system_config = {
    'Mode': 1,
    'SampleRate': 100000000,
    'Depth': 4000,
    'SegmentSize': 4000,
    'SegmentCount': 1,
    'TriggerHoldoff': 0,
    'TriggerDelay': 0,
    'TriggerTimeout': -1,
    'ExtClk': 0
    }

ch1_config = {
    'InputRange': 4000,
    'Coupling': 1,
    'Impedance': 50,
    'DcOffset': 0,
    }

ch2_config = {
    'InputRange': 4000,
    'Coupling': 1,
    'Impedance': 50,
    'DcOffset': 0
    }

trigger_config = {
    'Condition': 1,
    'Level': 30,
    'Source': -1,
    'ExtRange': 10000,
    'ExtImpedance': 50
    }

application_config = {
    'StartPosition': 0,
    'TransferLength': 2040,
    'SegmentStart': 1,
    'SaveFileName': 'Acquire',
    'SaveFileFormat': 'TYPE_FLOAT'
    }

channel_configs = [ch1_config, ch2_config]
possible_sample_rates = [100000000,65000000, 50000000, 40000000, 25000000,20000000,10000000,5000000,2000000,1000000]
possible_voltage_ranges = [0.1, 0.2, 0.5,1, 2, 5]

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
            
    def configure_system(
            self,
            mode = None,
            sample_rate = None,
            segment_size = None,
            segment_count = None,
            trigger_holdoff = None,
            trigger_timeout = None,
            voltage_range = None
            ):
        
        """
        Set the acquisition parameters of the system. 
        
        Parameters:
            - mode: 1 for single channel, 2 for dual channel, defaults to dual
            - sample_rate: integer for the sample rate. Must be one of [100MS/s, 65MS/s, 50MS/s, 40MS/s, 25MS/s, 20MS/s, 10MS/s, 5MS/s, 2MS/s, 1MS/s], defaults to 100MS/s
            - segment_size: The amount of samples taken per segment after the digitizer has been triggered, defaults to 4000
            - segment_count: The total number of segments the digitizer expects, defaults to 1
            - trigger_holdoff: number of samples after a trigger before digitizer can be triggered again, defaults to 0
            - voltage_range: voltage range in volts. This specifies the max AMPLITUDE of the input voltage, not peak to peak. Allowed values are [0.1,0.2,0.5, 1,2,5] with default 2 
            - trigger_timeout: how long to wait before the software forces a trigger event, in units of 100ns, defaults to -1 which means wait indefinitely

        This method can be run multiple times to change the configuration of the digitizer before starting acquisition.
        
        Example:
        dg = Digitizer()
        val = dg.configure_system(
            mode = 1,
            sample_rate = int(1e6),
            segment_size = 5000,
            segment_count = 1,
            voltage_range = 2
            )
        """
        
        self.mode = mode
        self.sample_rate = sample_rate
        self.segment_count = segment_count
        self.trigger_holdoff = trigger_holdoff
        self.trigger_timeout = trigger_timeout
        self.voltage_range = voltage_range
        
        
        if not isinstance(segment_size, int):
            segment_size = 4000
            print('Invalid segment size. Using default segment size 4000 \n')
        
        overflow = segment_size % 16
        if overflow > 0:
            segment_size = segment_size + 16 - overflow
            self.extra = overflow
            self.overflow = 16 - overflow
        else:
            self.overflow = 0
            self.extra = 16

        self.segment_size = segment_size

        if self.mode == 1 or self.mode == 2:
            system_config["Mode"] = self.mode
        else:
            system_config['Mode'] = 2
            print('Invalid Mode. Setting to 2 \n')
            
        if self.sample_rate in possible_sample_rates:
            system_config["SampleRate"] = int(self.sample_rate)
        else:
            print('Invalid sample rate. Using 100MS/s \n')
            system_config["SampleRate"] = 100000000
        
        if self.segment_size is not None:
            if isinstance(self.segment_size, int):
                system_config["SegmentSize"] = self.segment_size
                system_config["Depth"] = self.segment_size
            else:
                print('Invalid segment size. Using 4000 \n')
                system_config["SegmentSize"] = 4000
                system_config["Depth"] = 4000
        else:
            system_config["SegmentSize"] = 4000
            system_config["Depth"] = 4000
            if self.verbose:
                print('Using default segment size 4000 \n')
        
        if self.segment_count is not None:
            if isinstance(self.segment_count, int):
                system_config["SegmentCount"] = self.segment_count
            else:   
                print('Invalid segment count. Setting to 1 \n')
                system_config["SegmentCount"] = 1
        else:
            system_config["SegmentCount"] = 1
            if self.verbose:
                print('Using default segment count 1 \n')
               
        if isinstance(self.trigger_holdoff,int):
            system_config["TriggerHoldoff"] = self.trigger_holdoff
        elif self.trigger_holdoff is None:
            system_config["TriggerHoldoff"] = 0
            if self.verbose:
                print('Using default trigger holdoff 0 \n')
        else:
            print('Invalid trigger holdoff. Using 0 \n')
            system_config["TriggerHoldoff"] = 0
        
        if isinstance(trigger_timeout, int):
            system_config['TriggerTimeout'] = trigger_timeout
        elif self.trigger_timeout is None:
            system_config['TriggerTimeout'] = -1
            if self.verbose:
                print('Using default trigger timeout -1 \n')
        else:
            print('Invalid trigger timeout. Using -1 \n')
            system_config['TriggerTimeout'] = -1

        status = PyGage.SetAcquisitionConfig(self._handle, system_config)
        if status < 0:
            print("Error when setting acquisition configuration \n")
            return status

        self._system_info = PyGage.GetSystemInfo(self._handle)
        self._acq = PyGage.GetAcquisitionConfig(self._handle)

        channel_increment = gs.CalculateChannelIndexIncrement(
            system_config["Mode"],
            self._system_info["ChannelCount"],
            self._system_info["BoardCount"],
        )

        
        for i in range(0, self._system_info["ChannelCount"], channel_increment):
            if voltage_range in possible_voltage_ranges:
                channel_configs[i]["InputRange"] = int(2*1000*voltage_range)
            else:
                print(f'Invalid voltage range on channel {i+1}. Using +- 2V \n')
                voltage_range = 2
                channel_configs[i]["InputRange"] = int(2*1000*voltage_range)
           
            status = PyGage.SetChannelConfig(self._handle, int(i+1), channel_configs[i])
            if status < 0:
                return status

        status = PyGage.Commit(self._handle)
        self._system_info = PyGage.GetSystemInfo(self._handle)
        error_string = PyGage.GetErrorString(status)
        return error_string
            
    
    def configure_trigger(
        self,
        source = None,
        edge = None,
        trigger_range = None,
        level = None,
        impedance = None,
        coupling = None,
        ):
        
        """
        Set the trigger parameters of the system. If source is set to software, all other params will be ignored. 
        
        Parameters:
            - source: 'external' or 'software', defaults to external
            - edge: 'rising' or 'falling', defaults to rising
            - trigger_range: amplitude of input, in volts, defaults to +- 5V input
            - level: percentage of input range at which to trigger, defaults to 30%
            - impedance: 50Ohm or 1MOhm, defaults to 50 Ohm
            - coupling: AC or DC, defaults to DC
            
        Warning: If you initialize the digitizer and set the level to be a small number it will sometimes fail to read data and raise the error:
            "python: Common/shcommon/CsDevIoCtl.cpp:950: int32 CsDevIoCtl::CardReadMemory(PVOID, uInt32, EVENT_HANDLE, uInt32*): Assertion `u32RetCode != DEV_IOCTL_ERROR' failed."
        However, if you set the trigger level higher, take some data, and then incrementally move it down, you are able to go as low as you like with no error. Alternatively, reinitialize card and it might just work.   
            
            
        Example:
        dg = Digitizer()
        
        val = dg.configure_sysetem(*params)
        val = dg.configure_trigger(
            source = 'external',
            edge = 'rising',
            trigger_range = 5,
            level = 50,
            impedance = 50,
            coupling = DC
            )
        
        """
        if source == 'software':
            trigger_config['Source'] = 0
            self.configure_system(
                mode = self.mode,
                sample_rate = self.sample_rate,
                segment_size = self.segment_size - 16 + self.extra,
                segment_count = self.segment_count,
                trigger_holdoff = self.trigger_holdoff,
                trigger_timeout = 1,
                voltage_range = self.voltage_range)
                #reconfigure the system using the exact same settings, force software trigger after 100ns
        elif source == "external":
            trigger_config['Source'] = -1
        elif source == None:
            trigger_config['Source'] = -1
            if self.verbose:
                print('Using default trigger source external \n')
        else:
            print("Invalid trigger source. Using default external. \n")
            trigger_config['Source'] = -1                

        if edge == "rising":
            trigger_config['Condition'] = 1
        elif edge == "falling":
            trigger_config['Condition'] = 0
        elif edge is None:
            trigger_config['Condition'] = 1
            if self.verbose:
                print('Using default trigger level rising \n')
        else:
            print('Invalid trigger edge setting. Using default rising \n')
            trigger_config['Condition'] = 1
 


        if trigger_range == 1 or trigger_range == 5:
            trigger_config['ExtRange'] = int(2*1000*trigger_range)  
        elif trigger_range is None:
            trigger_config['ExtRange'] = int(2*1000*5)
            if self.verbose:
                print('Using default trigger range +-5V')
        else:
            print('Invalid trigger_range. Using default +- 5V \n')
            trigger_config['ExtRange'] = int(2*1000*5)
                
        if isinstance(level, int) and level <= 100 and level >= 0:
            trigger_config['Level'] = level
        elif level is None:
            trigger_config['Level'] = 30
            if self.verbose:
                print('Using default tigger level 30% \n')
        else:
            print('Invalid trigger level. Using default 30% \n')
            trigger_config['Level'] = 30

            
        if impedance == 50 or impedance == 1000000:
            trigger_config['ExtImpedance'] = impedance
        elif impedance is None:
            trigger_config['ExtImpedance'] = 50
            if self.verbose:
                print('Using default 50 Ohm impedance \n')
        else:
            print('Invalid impedance. Using default 50 Ohm \n') 
            trigger_config['ExtImpedance'] = 50


        if coupling == 'AC':
            trigger_config['ExtCoupling'] = 2
        elif coupling == 'DC':
            trigger_config['ExtCoupling'] = 1
        elif coupling is None:
            trigger_config['ExtCoupling'] = 1
            if self.verbose:
                print('Using default DC coupling \n')
        else:
            print('Invalid couping. Using default DC. \n')
            trigger_config['ExtCoupling'] = 1


        status = PyGage.SetTriggerConfig(self._handle, 1, trigger_config)
        if status < 0:
            return status

        status = PyGage.Commit(self._handle)

        self._system_info = PyGage.GetSystemInfo(self._handle)
        error_string = PyGage.GetErrorString(status)
        return error_string
    
    def get_acquisition_parameters(self):
        """return the current aquisition parameters of the digitizer as a dictionary, if availible"""
        try:
            return PyGage.GetAcquisitionConfig(self._handle)
        except Exception as e:
            print("Error getting acquisition parameters. Code: ", e, "\n")

    def get_channel_parameters(self, chan: Literal[1, 2]):
        """return the current channel parameters of the digitizer as a dictionary, if availible"""
        try:
            return PyGage.GetChannelConfig(self._handle, chan)
        except Exception as e:
            print("Error getting channel parameters. Code: ", e, "\n")

    def get_trigger_parameters(self):
        """return the current trigger parameters of the digitizer as a dictionary, if availible"""
        try:
            return PyGage.GetTriggerConfig(self._handle, 1)
        except Exception as e:
            print("Error getting trigger parameters. Code: ", e, "\n")

    def arm_digitizer(self):
        """ Starts Capture """
        status = PyGage.StartCapture(self._handle)
        if status < 0:
            return status

    def get_data(self):  # TODO: fix the function so we don't need to reinitialize and set the parameters every time.
        """Returns the digitizer data in 3-dim np.array.
        
        The first dimension iterates over all channels.
        The second dimension iterates over all segments.
        The third dimension stores data in each segment.
        """

        mode = PyGage.GetAcquisitionConfig(self._handle)["Mode"]


        channel_increment = gs.CalculateChannelIndexIncrement(
            mode, self._system_info["ChannelCount"], self._system_info["BoardCount"]
        )

        acq = PyGage.GetAcquisitionConfig(self._handle)

        min_start_address = acq["TriggerDelay"] + acq["Depth"] - acq["SegmentSize"]
        if application_config["StartPosition"] < min_start_address:
            print(
                "\nInvalid Start Address was changed from {0} to {1}".format(
                    application_config["StartPosition"], min_start_address
                )
            )
            application_config["StartPosition"] = min_start_address

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

                data = (data / 2**16) * (channel_configs[i-1]['InputRange'] * 1e-3) #the input range of the channel

                segment_data.append(data)

            segment_data = np.array(segment_data)

            channel_data.append(segment_data)

        return np.array(channel_data)

    def close(self):
        """
        Close the connection to the device
        """
        PyGage.FreeSystem(self._handle)
        
