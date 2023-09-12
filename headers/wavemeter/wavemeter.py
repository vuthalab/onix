######################################################################################################
# @file DataDemo.py
# @copyright HighFinesse GmbH.
# @author Lovas Szilard <lovas@highfinesse.de>
# @date 2018.09.15
# @version 0.1
#
# Homepage: http://www.highfinesse.com/
#
# @brief Python language example for demonstrating usage of
# wlmData.dll Set/Get function calls.
# Tested with Python 3.7. 64-bit Python requires 64-bit wlmData.dll and
# 32-bit Python requires 32-bit wlmData.dll.
# For more information see ctypes module documentation:
# https://docs.python.org/3/library/ctypes.html
# and/or WLM manual.pdf
#
# Changelog:
# ----------
# 2018.09.15
# v0.1 - Initial release
#
# Modified for multi-channel switch by SJ & KC (Nov 2020)
#
# Added support for laser locking by SJ (Apr 2021)
import os 
#os.chdir('/home/onix/gdrive/code/onix_control/headers/highfinesse_wavemeter_v4/')

# wlmData.dll related imports
from onix.headers.wavemeter.wlmData import LoadDLL
import onix.headers.wavemeter.wlmConst as wlmConst


# others
import time
import ctypes
import zmq
import sys
import numpy as np
import matplotlib.pyplot as plt
from onix.headers.wavemeter.zmq_publisher import zmqPublisher
import matplotlib.animation as animation
    
##

class WM:
    def __init__(self,mode='client',port=9000,publish=False,stream_port=5563,):
        
        self.port = port
        self.mode = mode
        self.publish = publish
        
        if mode=='server':
            
            self.dll = LoadDLL()
            from bristol_fos_windows import FOS
            self.fos = FOS()


        elif mode=='client':
            zmq_context = zmq.Context()
            self.socket = zmq_context.socket(zmq.REQ)
            self.socket.connect("tcp://192.168.0.103:%s"%self.port) #wavemeter comp
            #self.socket.connect("tcp://192.168.0.102:%s"%self.port) # fancy windows comp
            print("Connected to handler at 192.168.0.103:%s"%self.port)
        
            if publish:
                self.publisher = zmqPublisher(port=stream_port,topic='wavemeter')
                
        self.interferogram_enable=False
        
    def _mode_check(func):
        def wrapper(self,*args,**kwargs):
            if self.mode=='client':
                msg = func.__name__+';'+str(args)+';'+str(kwargs)
                resp = self._ask(msg)
                return resp
            else:
                return func(self,*args,**kwargs)
        return wrapper
        

    def _ask(self,message):
        """ Send request to zmq server to pass message to wavemeter client """
        if isinstance(message,str): message = message.encode()
        self.socket.send(message)
        
        reply = self.socket.recv()
        try:
            reply = float(reply.decode()) #convert answers to floats when applicable
        except:
            reply = reply.decode()
        return reply
        


    # for webapp:
    @property
    def wavelengths(self):
        return [self.read_wavelength(i+1) for i in range(8)]
        
    @property
    def frequencies(self):
        return [self.read_frequency(i+1) for i in range(8)]
        
    @property
    def powers(self):
        return [self.read_laser_power(i+1) for i in range(8)]
        
        
    @_mode_check    
    def read_frequency(self,channel):
        """ Return frequency of channel in GHz """
        frequency = self.dll.GetFrequencyNum(ctypes.c_long(channel),ctypes.c_double(0.0))
        frequency = float(frequency)
        if frequency<0:
            return wlmConst.meas_error_to_str(frequency)
        else:
            return 1e3*float(frequency)
    
    @_mode_check
    def read_wavelength(self,channel):
        """ Return the wavelength of channel in nm """
        wavelength = self.dll.GetWavelengthNum(channel,0.0)
        return float(wavelength)
        
    @_mode_check
    def read_temperature(self):
        """ Read wavemeter temperaure in C """
        temperature = self.dll.GetTemperature(ctypes.c_double(0.0))
        return float(temperature)

    @_mode_check
    def read_exposure(self,channel,arr=1):
        """
        Return the exposure setting of a specified channel and array

        Inputs:
        channel: 1-7
        array: 1 or 2
        exposure on array 1 is used to obtain the wide/coarse interferogram
        exposure on array 2 is used to obtain the fine interferogram
        actual exposure on array 2 is the sum of the exposure settings for arrays 1 and 2

        """
        exposure = self.dll.GetExposureNum(channel,arr,False)
        return float(exposure)


    # these exposure functions don't work properly - needs investigation
    
    @_mode_check
    def read_exposure_mode(self,channel):
        """ Read exposure mode: 1==Auto, 0==Manual """
        expomode = self.dll.GetExposureModeNum(channel,0)
        return int(expomode)
    
    @_mode_check
    def set_exposure(self,channel,exp,arr=1):
        """
        Set the exposure of a certain channel and array

        Inputs:
        set_exposure(channel,array,exposure), where

        channel: 1-7
        exposure: an integer time in ms
        array: 1 or 2 (1: exposure on array 1; 2: exposure on all  other arrays; total exposure is the sum)
        """

        # Read exposure of CCD arrays
        self.dll.SetExposureNum(channel,1,exp)
        time.sleep(0.5)
        return self.read_exposure(channel)
    
    @_mode_check
    def set_exposure_mode(self,channel,auto):
        """
        Set the exposure of a certain channel to auto

        auto = True means automatic control
        auto = False means manual control
        
        returns exposure mode of channel

        """
        if auto:
            self.dll.SetExposureModeNum(channel,True)
        else:
            self.dll.SetExposureModeNum(channel,False)

        return self.read_exposure_mode(channel)
        
    
    @_mode_check 
    def read_laser_power(self,channel):
        """ Returns laser power of channel in uW """
        power = self.dll.GetPowerNum(channel,0)
        return float(power)

    @_mode_check 
    def read_linewidth(self,channel):
        """ Returns linewidth of channel in GHz."""
        linewidth = self.dll.GetLinewidthNum(channel, 0)
        return float(linewidth)
    
    @_mode_check
    def get_lock_setpoint(self,channel):
        """ Returns lock setpoint of channel in GHz """
        info = ctypes.c_char_p(1024*b'a')
        ret = self.dll.GetPIDCourseNum(channel,info)
        #print(ret)
        setpoint = info.value
        try:
            return 1e3*float(setpoint)
        except:
            return setpoint.decode() #if a mathematical construct rather than number
    
    @_mode_check
    def set_lock_setpoint(self,channel,setpoint):
        """Set the lockpoint of channel in GHz"""
        if channel not in [1,2,3,4,5,6,7,8]:
            return "Invalid channel" #don't accidentally set frequency to 7!
        else:
            try:
                send_str = str(1e-3*float(setpoint))
            except:
                send_str = str(setpoint) #for mathematical construct
                #TODO: add code to check if mathematical construct is valid
            info = ctypes.c_char_p(bytes(send_str.encode()))
            ret = self.dll.SetPIDCourseNum(channel,info)
            return self.get_lock_setpoint(channel)


    @_mode_check
    def _poll_pid(self,channel,const):
        lref = ctypes.pointer(ctypes.c_long(0))
        dref = ctypes.pointer(ctypes.c_double(0))
        
        dtype = wlmConst.pid_datatypes[const]
        
        ret = self.dll.GetPIDSetting(const,channel,lref,dref)
        
        #print(lref.contents.value)
        #print(dref.contents.value)
        
        if dtype=='double':
            return dref.contents.value
        else:
            return lref.contents.value
    
    @_mode_check
    def _set_pid(self,channel,const,setting):
        dtype = wlmConst.pid_datatypes[const]
        lref = 0
        dref = 0.0
        
        
        if dtype=='double':
            dref=setting
        elif dtype=='long':
            lref=setting
        
        ret = self.dll.SetPIDSetting(const,channel,lref,dref)
        return wlmConst.errors[ret]


    @_mode_check
    def get_external_output(self,channel):
        """Returns the last exported analog voltage of the DAC channel in mV"""
        ret = self.dll.GetDeviationSignalNum(channel,0.0)
        return ret
       
    # this seems to overwrite locking stuff - have to restart wavemeter to get back
    #@_mode_check
    #def set_external_output(self,channel,voltage):
    #    """Sets the analog voltage of the DAC channel in mV"""
    #    ret = self.dll.SetDeviationSignalNum(channel,voltage)
    #    return wlmConst.errors[ret]

    #@_mode_check
    #def get_interferogram_size(self):
        
    @_mode_check
    def _setup_interferogram(self):
        ret = self.dll.SetPattern(wlmConst.cSignal1WideInterferometer,wlmConst.cPatternEnable)
        self.interferogram_enable = True
        
        item_count = self.dll.GetPatternItemCount(wlmConst.cSignal1WideInterferometer)
        self.interferogram_itemcount = item_count
        
        return ret

    @_mode_check
    def _fetch_interferogram(self,channel):
        if not self.interferogram_enable:
            self._setup_interferogram()
            
        loc = self.dll.GetPatternNum(channel,wlmConst.cSignal1WideInterferometer)

        c_arr = ctypes.c_ulong*self.interferogram_itemcount
        arr_init = self.interferogram_itemcount*[0]
        PArray = ctypes.pointer(c_arr(*arr_init))
        self.dll.GetPatternDataNum.argtypes = [ ctypes.c_long, ctypes.c_long, ctypes.POINTER(c_arr) ]
        #PArray = ctypes.pointer(ctypes.c_ulong(0))
        ret = self.dll.GetPatternDataNum(channel,wlmConst.cSignal1WideInterferometer,PArray)
        
        arr = [PArray.contents[i] for i in range(self.interferogram_itemcount)]
        return arr
        #return PArray
    
    @_mode_check
    def change_bristol_channel(self,chan):
        self.fos.change_channel(chan)

    def _format_str_array(self,arr):
        if isinstance(arr,str):
            st = arr.strip('[').strip(']').split(',')
            arr = np.array(st,dtype=int)
            arr = np.trim_zeros(arr,trim='b')
            arr = arr.astype('float')
        return arr
    
    def plot_interferogram(self,channel):
        arr = self._format_str_array(self._fetch_interferogram(channel))
        
        fig = plt.figure()
        plt.plot(arr)
        plt.show()
        return arr
            
    def _update_live_plot_interferogram(self,i,channels,lines):
        if(isinstance(channels,int)): 
            channels = [channels]
            lines = [lines]
        
        for i in range(len(channels)):
            new_data = self._format_str_array(self._fetch_interferogram(channels[i]))
            lines[i].set_ydata(new_data)
        return lines,
        
    def live_plot_interferogram(self,channels):
        if(isinstance(channels,int)):
            channels = [channels]
        
        fig = plt.figure()
        lines = []
        
        for i in range(len(channels)):
            new_data = self._format_str_array(self._fetch_interferogram(channels[i]))
       
            lines.append(plt.plot(new_data,label="Channel %i"%(channels[i]))[0])
        ani = animation.FuncAnimation(fig,self._update_live_plot_interferogram,fargs=(channels,lines),frames=50,blit=False)
        #plt.title("Wavemeter channel %i"%channel)
        plt.tight_layout()
        plt.legend()
        plt.show()

    def get_pid_settings(self,channel):
        P = self._poll_pid(channel,wlmConst.cmiPID_P)
        I = self._poll_pid(channel,wlmConst.cmiPID_I)
        D = self._poll_pid(channel,wlmConst.cmiPID_D)
        sens = self._poll_pid(channel,wlmConst.cmiDeviationSensitivityFactor)
        pol = self._poll_pid(channel,wlmConst.cmiDeviationPolarity)
        chan = int(self._poll_pid(channel,wlmConst.cmiDeviationChannel))
        active = chan==channel
        
        stuff = [P,I,D,pol,sens,active,chan]

        print("P = %.2f, I = %.2f, D = %.3f \n Regulation active: %s"%(P,I,D,active))

        return stuff
    
    
    def lock_laser(self,channel):
        return self._set_pid(channel,wlmConst.cmiDeviationChannel,channel)
    
    def lock_laser_here(self,channel):
        setpoint = self.read_frequency(channel)
        self.set_lock_setpoint(channel,setpoint)
        self.lock_laser(channel)
        return self.get_lock_setpoint(channel)
    
    def unlock_laser(self,channel):
        r = self._set_pid(channel,wlmConst.cmiDeviationChannel,0)
        self.clear_integral_history(channel)
        return r

    def set_p_gain(self,channel,gain):
        return self._set_pid(channel,wlmConst.cmiPID_P,gain)

    def set_i_gain(self,channel,gain):
        return self._set_pid(channel,wlmConst.cmiPID_I,gain)
        
    def set_d_gain(self,channel,gain):
        return self._set_pid(channel,wlmConst.cmiPID_D,gain)

    def increase_frequency(self,channel,adjust=10):
        """Increase lock setpoint frequency of channel by amount in MHz"""
        setpoint = float(self.get_lock_setpoint(channel)) #MHz
        setpoint +=(1e-3*adjust)
        self.set_lock_setpoint(channel,setpoint)
        return self.get_lock_setpoint(channel)
        
    def decrease_frequency(self,channel,adjust=10):
        """Increase lock setpoint frequency of channel by amount in MHz"""
        setpoint = float(self.get_lock_setpoint(channel)) #MHz
        setpoint -=(1e-3*adjust)
        self.set_lock_setpoint(channel,setpoint)
        return self.get_lock_setpoint(channel)
        
    def ramp_laser(self,channel,amplitude = 100.0,frequency = 1.0):
        """Ramp laser around current setpoint frequency. Amplitude in MHz, frequency in Hz"""
        # must send frequencies in THz
        curr_setpoint = self.get_lock_setpoint(channel)
        try:
            start =1e-3*float(self.get_lock_setpoint(channel)) #THz
        except:
            start = float(curr_setpoint.split()[0]) #THz
        
           
        send_str = str(start - 1e-6*amplitude/2) +" + %.7f triangle(t/ %.3f)"%((1e-6*amplitude),frequency)
        self.set_lock_setpoint(channel,send_str)
        
        return self.get_lock_setpoint(channel)
        
        
    def ramp_off(self,channel):
        curr_setpoint = self.get_lock_setpoint(channel)
        bottom = curr_setpoint.split()[0]
        amp = curr_setpoint.split()[2]
        mid = float(bottom) + float(amp)/2
        self.set_lock_setpoint(channel,1e3*mid)
        return self.get_lock_setpoint(channel)
        
        
    @_mode_check 
    def clear_integral_history(self,channel):
        """ Clears the integral history of the channel. Returns 1 """
        ret = self.dll.ClearPIDHistory(channel)
        return ret

    def stream_some_frequencies(self,channels=[3,4,5,7,8],sleep_time = None):
        """
        Display a constant stream of frequency readings for selected channels. 
        If publishing is on, publish values to zmq port. 
        """
        
        go = True
        while go:
            for i in channels:
                try:
                    #print("Test")
                    new_data = self.read_frequency(i)
                    if self.publish:
                        self.publisher.publish_data((i,round(new_data,6)),prnt=True)
                    else:
                        print(new_data)
                    if(sleep_time==None):
                        sleep_time = 1.0/len(channels)
                    time.sleep(sleep_time)

                except(KeyboardInterrupt):
                    go=False
                    break

                except Exception as e:
                    print(e)

if __name__=='__main__':
    wm = WM(mode = 'server')
    



