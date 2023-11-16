from typing import List
import re
import telnetlib
import time
import os

from onix.headers.usbtmc import USBTMCDevice
#from headers.usbtmc import USBTMCDevice



class CTC100(USBTMCDevice):
    """
    An extremely simple class to read values from the CTC100
    Prorammable Temperature Controller. Use ethernet rather 
    than a serial port.

    How to use::

        >>> import CTC100
        >>> c = CTC100.CTC100("/dev/ttyACM0")
        >>> c.read(1)
        300.841

    Author: Wesley Cassidy
    Date: 26 April 2018
    
    Modified by: Rhys Anderson
    Date: February 25, 2020

    Modified by: Samuel Li
    Date: May 11, 2021
    
    Modified by: Scott Smale
    Date: June 23, 2023
    """

    def __init__(self, ip_address,multiplexed=True):
        """Connect to the the CTC100."""
        if multiplexed:
            super().__init__(ip_address, mode='multiplexed') # multiplexed connection. here 'ip_address' is actually a local port number.
        else:
            super().__init__(ip_address, tcp_port=23, mode='ethernet') # direct connection
        self._set_variable('system.com.verbose', 'Medium')
        self._set_variable('system.display.Figures', 4)

        
    def _get_variable(self, var):
        """
        Read a parameter of the CTC100. This function is mostly for
        convenience, but does include some input formatting to prevent
        simple bugs.
        """
        
        var = var.replace(' ', '') # Remove spaces from the variable name. They're optional and can potentially cause problems
        return self.query(f'{var}?')

        
    def _set_variable(self, var, val):
        """
        Set a parameter of the CTC100. This function is mostly for
        convenience, but does include some input formatting to prevent
        simple bugs.
        """
        
        var = var.replace(" ", "") # Remove spaces from the variable name. They're optional and can potentially cause problems
        val = "({})".format(val) # Wrap argument in parentheses, just in case. This prevents an argument containing a space from causing unexpected issues

        # Replace with query if verbose mode is high
        return self.send_command(f"{var} = {val}")

        
    def _increment_variable(self, var, val):
        """
        Add an amount to a parameter of the CTC100. This function is
        mostly for convenience, but does include some input formatting
        to prevent simple bugs.
        """
        
        var = var.replace(" ", "") # Remove spaces from the variable name. They're optional and can potentially cause problems
        val = "({})".format(val) # Wrap argument in parentheses, just in case. This prevents an argument containing a space from causing unexpected issues
        return self.query("{} += {}".format(var, val))

    def setAlarm(self, channel, Tmin, Tmax):
        """Enables alarm with 4 beeps on a channel for a given range."""
        
        if not isinstance(channel, str): #Sets string for channel
            channel = "In{}".format(channel)
            
        self._set_variable(f"{channel}.alarm.sound", "4 beeps") #Sets alarm to 4 beeps
        
        self._set_variable(f"{channel}.alarm.min", str(Tmin)) #Sets minimum Temperature
        self._set_variable(f"{channel}.alarm.max", str(Tmax)) #Set maximum Temperature
        
        response = self._set_variable(f"{channel}.alarm.mode", "Level") # Turns alarm on
        return response

        
    def disableAlarm(self, channel):
        if not isinstance(channel, str): #Sets string for channel
            channel = "In{}".format(channel)

        self._set_variable("{}.alarm.mode".format(channel), "Off") # Turns alarm off
    

    def read(self, channel):
        """
        Read the value of one of the input channels. If the channel's
        name has been changed from the default or you wish to read the
        value of an output channel, the full name must be passed as a
        string. Otherwise, an integer will work.
        """

        if not isinstance(channel, str): #Sets string for channel
            channel = f"In{channel}"
            
        response = self._get_variable(f"{channel}.value")
        if response is None: return None
   
        # Extract the response using a regex in case verbose mode is on
        match = re.search(r"[-+]?\d*\.\d+", response)
        return float(match.group()) if match is not None else None


    def ramp_temperature(self, channel, temp=0.0, rate=0.1):
        self._set_variable(f"{channel}.PID.mode", "off") #This should reset the ramp temperature to the current temperature.
        self._set_variable(f"{channel}.PID.Ramp", str(rate))
        self._set_variable(f"{channel}.PID.setpoint", str(temp))
        self._set_variable(f"{channel}.PID.mode", "on") 
        
    def disable_PID(self, channel):
        self._set_variable(f"{channel}.PID.mode", "off")
        self._set_variable(f"{channel}.value","0")
        self._get_variable(f"{channel}.Off")

    # This set of heater functions assumes that power is in Watts.
    # Also assumes that the output enable is enabled.
    def set_heater_off(self, channel):
        self._get_variable(f"{channel}.off")
    
    def set_heater_low_lim(self, channel, val):
        self._set_variable(f"{channel}.LowLmt", val)
        
    def set_heater_high_lim(self, channel, val):
        self._set_variable(f"{channel}.HiLmt", val)
    
    def set_heater_output_power(self, channel, val):
        self._set_variable(f"{channel}.value", val)

    @property
    def output_enabled(self):
        return self._get_variable('outputEnable') == 'on'
        
    def enable_output(self): self._set_variable("outputEnable", "on")
        
    def disable_output(self): self._set_variable("outputEnable", "off")


    @property
    def channels(self) -> List[str]:
        return self.query('getOutput.names').split(',')
