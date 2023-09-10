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

import numpy as np
import time
import os
import sys
import socket

import pyvisa

class Digitizer:

    def __init__(self, address="192.168.0.109", params_dict={}):
        
        # open the connection
        self.addr = address
        self.open_connection()
        time.sleep(0.05)
        
        #self.instr.timeout = 60000
        
        # test the connection
        s = self.test_connection()# prints the name of the device if successful
        
        # check for errors
        errs = self.list_errors()
        if errs:
            print("There were errors after making connection")
            print(errs)
            raise("ERROR")
            
        # if processor is little-endian then let the digitizer know
        if sys.byteorder == "little":
            #'SWAP' means little-endian not switch endian mode
            print('Byte order set to swap')
            self.write("FORM:BORD SWAP")

        # default dictionary of parameters
        self._default_p = { 'num_samples': 16400,#1000, will be coerced up to multiple of 4
                            'sampling_rate': 1e5,# /s
                            'ch1_voltage_range': 8,# +/-V
                            'ch2_voltage_range': 8,# +/-V
                            'trigger_channel': 0,# 1 -> ch1, 2 -> ch2, 0 -> ext, else -> immediate
                            'data_format': "float32",# "float32" or "adc16"
                            'coupling': "DC",
                            'num_records': 1,
                            'triggers_per_arm': 1
                            }

        self.set_parameters(params_dict)
        
        yay = self.configure()
        if not yay:
            print("There was an error during configuration")
            raise("ERROR")
        
        # Double check that the clock is in external mod_
        #s = self.clock_status()
        #print(s)
        #if s != "EXT":
            #print(f"The clock is not external: |{s}|")
            #raise("ERROR")
            
    # connect to the device
    def open_connection(self):
        """
        Make the connection to the device.
        Redefine for subclasses.
        """
        # TCPIP[board]::host address[::LAN device name][::INSTR]
        # TCPIP[board]::host address::port::SOCKET
        # "TCPIP::192.168.0.130::5025::INSTR"
        # "TCPIP::192.168.0.130::5025::SOCKET"
        
        # Create pyvisa resource manager
        self.rm = pyvisa.ResourceManager()
        
        self.addr_string = f"TCPIP::{self.addr}::INSTR"
        print(f"Opening connection to {self.addr_string}")
        self.instr = self.rm.open_resource(self.addr_string)
        print("Connection opened.")

    def close_connection(self):
        """
        Close the connection to the device.
        """
        self.instr.close()
    
    # basic routines for writing commands and reading responses
    def write(self, command):
        """
        Write a command to the device.
        """
        self.instr.write(command)

    def read(self):
        """
        Read from the device.
        """
        s = self.instr.read()
        return s
        
    def query(self, command):
        """
        Query the device.
        """
        return self.instr.query(command).strip()
    
    def ask(self, command, wait = 0.01):
        """
        Wrapper for including a wait time before reading the answer.
        
        Only use for very old/slow devices.
        """
        return self.instr.query(command, delay = wait)
    
    def query_binary_values_adc16(self, command):
        """
        Query for a response that will give int16 binary values.
        
        Returns a numpy array with int16 elements.
        """
        return self.instr.query_binary_values(command, datatype='h', container=np.array, chunk_size = 2000*1024)
        
    def query_binary_values_float32(self, command):
        """
        Query for a response that will give float32 binary values.
        
        Returns a numpy array with float32 elements.
        """
        return self.instr.query_binary_values(command, datatype='f', container=np.array, chunk_size = 2000*1024)
    
    # convenience functions
    def test_connection(self):
        s = self.get_name()
        #print(type(s))
        print(s)
        if 'Agilent Technologies,L4532A' not in s:
            print("Testing connection failed. Wrong device or connection failed.")
            #raise("ERROR")
        return s
    
    def get_name(self):
        return self.query("*IDN?")

    def send_reset(self):
        self.write("*RST")

    def self_test(self):
        return self.query("*TST?")

    def get_error(self):
        return self.query("SYSTEM:ERROR?")
    
    def list_errors(self):
        err_list = []
        for i in range(100):
            msg = self.get_error()
            print (msg)
            if '+0,"No error"' in msg:
                break
            err_list.append(msg)
        return err_list

    def initiate(self):
        self.write("INITiate")

    def clock_status(self):
        return self.query("CONF:ROSC?")
        
    def set_parameters(self, params_dict = {}):
        """
        Sets the parameters according to params_dict. Must be full params dict.
        
        Updating the Digitizer itself requires self.configure().
        """
        # This could be extended in the future to accept a partial dict of
        # params and only overwrite those ones.
        if params_dict:# load from arg
            self.params = params_dict
        else:# put defaults
            self.params = self._default_p
    
    def get_parameters(self):
        """
        Returns the digitizer parameters of this instance.
        Remember that the digitizer must be set with configure for these to take
        effect.
        """
        return self.params
    
    def status_report(self):
        """
        Print a few important aspects of the Digitizer settings from the device.
        """
        print("Status report:")
        print(f"Name: {self.get_name()}")
        print(f"Error?: {self.get_error()}")
        print(f"Clock?: {self.clock_status()}")
    
    def configure(self):
        """
        Configures digitizer based on values in dictionary of parameters.
        """
        try:
            self.write("CONFigure:ACQuisition:SRATe " + str(self.params['sampling_rate']))
            # records per acquisition.
            # Each record requires a trigger
            #self.write("CONF:ACQ:RECords 1")
            
            # samples per record
            self.write("CONF:ACQ:SCO " + str(self.params['num_samples']))
            # input voltage range for CH1
            self.write("CONF:CHANnel:RANGe (@1), " + str(self.params['ch1_voltage_range']))
            # input voltage range for CH2
            self.write("CONF:CHANnel:RANGe (@2), " + str(self.params['ch2_voltage_range']))
            
            
            # set trigger channel
            tc = self.params['trigger_channel']
            if (tc == 1) or (tc == 2):
                self.write("CONFigure:TRIGger:SOURce CHANnel")
                # trigger source, level=0, positive
                self.write(f"CONFigure:TRIGger:SOURce:CHANnel:EDGE (@{tc}),0,POS")
            elif tc == 0:
                # external trigger
                self.write("CONFigure:TRIGger:SOURce EXTERNAL")
            else:
                # software trigger
                self.write("CONFigure:TRIGger:SOURce IMMediate")

            # data transfer format
            if self.params['data_format'] == 'adc16':
                # uses digitizer's native "ADC16" format, 2 bytes/sample
                self.write("FORMat:DATA:INTeger INTeger")
            elif self.params['data_format'] == 'float32':
                # returns 32-bit IEEE-754 floats, 4 bytes/sample
                self.write("FORMat:DATA:REAL REAL,32")
            
            #number of records
            self.write("CONF:ACQ:REC " + str(self.params['num_records']))
            
            #AC or DC
            self.write("CONF:CHANnel:COUPling (@1,2), " + str(self.params['coupling']))
                
            # the following parameters are hardwired, for now. Change them to be configurable if needed
            #lock to external clock source ***replace once clock is setup with the Artiq
            #self.write("CONF:ROSC EXT")
            # lock to internal clock source
            self.write("CONF:ROSC INT")
            # low pass filter on CH1
            self.write("CONF:CHAN:FILT (@1), LP_200_KHZ")
            # low pass filter on CH2
            self.write("CONF:CHAN:FILT (@2), LP_20_MHZ")
            # digitizer arms immediately after recieving INITiate command
            #self.write("CONF:ARM:SOURCE IMMEDIATE")
            #number of triggers per arm
            self.write("CONF:ARM:SOUR IMM," + str(self.params['triggers_per_arm'])) 

            #digitizer will not store samples before recieving a trigger
            self.write("CONF:ACQ:SPR 0")
            
            # wait for all of the config changes to be processed
            time.sleep(0.4)# 0.3 works sometimes, 0.4 seems to always work
            
            return True
        except:
            # wait for all of the config changes to be processed
            time.sleep(0.4)# 0.3 works sometimes, 0.4 seems to always work
            
            return False
    

    # Functions to acquire data from digitizer
    
    def convert_ADC16_to_Volt(self, np_array, vrange):
        """
        Converts from the digitizer's ADC16 output format to volts.
        
        np_array: dtype np.int16
        vrange: the voltage range ie. digitizer range is +/-vrange
        """
        #print(f'The first data point in the array that is passed to this function is: {np_array[0]}')
        #print(f'The voltage setting is {vrange}')
        
        # check that there are no undefined values
        err_indices = np.equal(np_array, -32768)# aka np_array==-32768
        #print(f'The type of the np_array is {type(np_array)}')
        #print(f'The type of the np_array[0] is {type(np_array[0])}')
        #print(f'The type of the vrange is {type(vrange)}')
        #print(f'The shape of np_array is {np_array.shape}')
        voltage = np.float64(np_array)*vrange/32767.0
        v1 = np.multiply(np_array, vrange)
        v2 = np.divide(v1, 32767.0)
        #print(f'np_array[0]*vrange/32767.0 = {np_array[0]*vrange/32767.0}')
        #print(f'The type of the voltage[0] is {type(voltage[0])}')
        #print(f'The first entry of the computed voltage is {voltage[0]}')
        #print(f'The 2nd entry of the computed voltage is {voltage[1]}')
        #print(f'The shape of voltage is {voltage.shape}')
        return (voltage, err_indices)

    def set_two_channel_waitForTrigger(self):
        """
        Initiates a measurement of both channels at the next trigger.
        """
        #Sets channels to wait for data to start acquiring up to num_samples
        self.initiate()
        if self.params['data_format'] == 'adc16':        
            self.write("FETCH:WAVeform:ADC? (@1,2)")

        elif self.params['data_format'] == 'float32':
            self.write("FETCH:WAVEFORM:VOLTAGE? (@1:2)")
            
    def set_immediate_trigger(self):
        """Set the digitizer to trigger whenever the software asks"""
        self.write("CONFigure:TRIGger:SOURce IMMediate")
        ret = self.query("CONF:TRIG:SOUR?")
        self.trigger = ret
        return ret

    def crude_trigger(self):
        """
        Do the crude thing of software triggering without changing any settings.
        """
        # This function is for putting data into the sample memory for testing
        # functions like get_two_channel_waveform().
        self.write("INIT")
        self.write("TRIGger:IMMediate")
        self.list_errors()# clear the errors we produced
        
    def get_two_channel_waveform(self, record_number=1, samples_per_record=0):
        """
        Reads in the two waveforms that are assumed to be in sample memory.
        
        Sets any undefined values to np.nan.
        """
        #t = time.time()
        #print(f"dig 0: {t}")
        
        if self.params['data_format'] == 'adc16':
            #print("Fetching adc16 data")
            s = self.query_binary_values_adc16(f"FETCH:WAV:ADC? (@1,2),0,"+str(self.params['num_samples'])+ ",(@{record_number})")
            #print(f"dig a: {time.time()-t}")
            s1 = s[::2]# separate ch1 points
            s2 = s[1::2]# separate ch2 points
            #print(f'The first data point in V1 is (s1[0]): {s1[0]}')
            self.dataV1, err_indices = self.convert_ADC16_to_Volt(s1, self.params['ch1_voltage_range'])
            print(f'The mean of data from V1 is {np.mean(self.dataV1)}')
            if np.any(err_indices):# set by convert_ADC16_to_Volt
                print("Warning! Digitizer ch1 data contains samples with no data available!")
                self.dataV1[err_indices] = np.nan
            self.dataV2, err_indices = self.convert_ADC16_to_Volt(s2, self.params['ch2_voltage_range'])
            if np.any(err_indices):# set by convert_ADC16_to_Volt
                print("Warning! Digitizer ch2 data contains samples with no data available!")
                self.dataV2[err_indices] = np.nan
            #print(f"dig b: {time.time()-t}")
                
        elif self.params['data_format'] == 'float32':
            #print("Fetching float32 data")
            #print(f"FETCH:WAV:VOLTAGE? (@1,2),0,{self.params['num_samples']},(@{record_number})")
            #s = self.query_binary_values_float32("FETCH:WAV:VOLTAGE? (@1,2),0,{self.params['num_samples']},(@{record_number})")
            #record_number = 1
            query = "FETCH:WAV:VOLTAGE? (@1,2),0,"+str(self.params['num_samples'])+",(@" +str(record_number)+")"
            #print(query)
            s = self.query_binary_values_float32(query)
            #print(f"dig a: {time.time()-t}")
            self.dataV1 = s[::2]# separate ch1 points
            self.dataV2 = s[1::2]# separate ch2 points
            err_indices = np.greater_equal(self.dataV1, 9.0e37)# undefined values are +9.91e37 Volts
            if np.any(err_indices):
                print("Warning! Digitizer ch1 data contains samples with no data available!")
                self.dataV1[err_indices] = np.nan
            err_indices = np.greater_equal(self.dataV2, 9.0e37)# undefined values are +9.91e37 Volts
            if np.any(err_indices):
                print("Warning! Digitizer ch2 data contains samples with no data available!")
                self.dataV2[err_indices] = np.nan
            #print(f"dig b: {time.time()-t}")
        
        #print(f"dig c: {time.time()-t}")
        
        # finally, return the two voltages (that are also cached in self)
        #print(f'The first entry before return is {self.dataV1[0]}')
        return self.dataV1, self.dataV2
        
    # Diagnostic functions for testing
    
    def test_aquire(self):
        """
        Test function for aquiring some data without a hardware trigger.
        """
        # Note that setting software triggering should NOT be
        # "CONF:ARM:TRIG SOFT" as on p115 of the manual. It gives an
        # undefined header error.
        # In principle all that is needed is "INIT" and "TRIG:IMM" to start an
        # aquisition from 'software', but not setting software triggering gives
        # a nominal error about ignoring triggers. But it still seems to trigger
        # just fine.
        self.write("CONF:TRIG:SOUR SOFT")
        print(self.list_errors())
        self.write("INIT")
        print(self.list_errors())
        self.write("TRIGger:IMMediate")
        print(self.list_errors())
        
        print("one")
        time.sleep(0.5)# wait to avoid timing errors while testing
        print("two")
        
        print(self.list_errors())
        
        # The 'Complete Data Aquisition Process' is detailed on p157 of the manual
        
        s = self.query("STATus:OPERation:CONDition? MTHReshold")
        print(f"is data: {s}")
        
        s = self.query("FETCh:WAVeform:ACQuisition:PREamble?")
        print(f"preamble: {s}")
        
        s = self.query("FETCh:WAVeform:RECord:PREamble? 1")
        print(f"record preamble: {s}")
        
        #preamble: b'+1,+12,+12,NORM,+0,+0,+0.0000000000000000E+000\n'
        #record preamble: b'+1,+12,+0,+3.7499999999999998E-008,+0.0000000000000000E+000,+0,+0\n'
        # These make sense for a number of samples asked for of 12. See pp162-163 in manual.
        # No errors in data aquisition.
        
        s = self.query("FETCh:WAVeform:CHANnel:ERRor? (@1)")
        print(f"is error: {s}")
        
        t0 = time.time()
        
        s = self.instr.query_binary_values("FETCH:WAV:ADC? (@1)", datatype='h', container=np.array)
        
        t1 = time.time()
        print(f"fetch time: {t1-t0}")
        
        # The first 11 bytes are a '#' followed by '9' followed
        #  by 9 bytes whose decimal combination gives the number of bytes that
        #  follows (see pp140-141 in manual)
        print(f"buf: {s}")
        print(type(s))
        print(s.dtype)
        print(f"buf head: {s[0:11]}")
        print(f"buff tot len: {len(s)}")
        print(f"num samples: {self.params['num_samples']}")
        #print(f"data bytes len: {len(s[11:-2])}")# minus head and trailing '\n'. should equal number of samples
        
        dataV, err_indices = self.convert_ADC16_to_Volt(s, self.params['ch1_voltage_range'])
        
        print(f"dataV: |{dataV}|")
        print(f"err idc: {err_indices}")
        
        if np.any(err_indices):# err_indices set by convert_ADC16_to_Volt
            print("Warning! Digitizer data contains samples with no data available!")
            raise("ERROR")
            dataV[err_indices] = np.nan# the silent option
        # Undefined values will always be -9e37 or so for float32 fetches.
        
        # make sure to undo the test changes before ending
        self.configure()
        
        return dataV
    
    def test_query_timings(self):
        # Iterate through a set of number of samples and time how long each
        # takes to read from the device.
        # Uncomment only one of the query choices to time that choice.
        
        num_samples = [2e1, 5e1, 1e2, 2e2, 5e2, 1e3, 2e3, 5e3, 1e4, 2e4, 5e4, 1e5, 2e5, 5e5, 1e6]
        
        self.write("CONF:TRIG:SOUR SOFT")
        
        query_times = []
        for n in num_samples:
            print(f"Do {n} sample meas.")
            
            # set the number of samples
            self.write(f"CONF:ACQ:SCO {n}")
            time.sleep(0.1)# being extra careful with timing
            
            # do a meas
            self.write("INIT")
            self.write("TRIG:IMM")
            
            # wait the correct time
            print(f"Wait at least {n/self.params['sampling_rate']} second500s for meas to finish")
            time.sleep(n/self.params['sampling_rate'])
            #time.sleep(3.0)# extra wait time to be sure
            print("Meas time done")
            
            print(self.list_errors())
            
            # start timer
            t0 = time.time()
            
            # vary data type and number of channels
            # single channel (1), int16 values
            s = self.query_binary_values_adc16("FETCH:WAV:ADC? (@1)")
            # single channel (2), int16 values
            #s = self.query_binary_values_adc16("FETCH:WAV:ADC? (@2)")
            # dual channel (1,2), int16 values
            #s = self.query_binary_values_adc16("FETCH:WAV:ADC? (@1,2)")
            # single channel (1), float32 values
            #s = self.query_binary_values_float32("FETCH:WAV:VOLTAGE? (@1)")
            # single channel (2), float32 values
            #s = self.query_binary_values_float32("FETCH:WAV:VOLTAGE? (@2)")
            # dual channel (1,2), float32 values
            #s = self.query_binary_values_float32("FETCH:WAV:VOLTAGE? (@1,2)")
            
            # vary chunk size, single channel (1), int16 values
            #s = self.instr.query_binary_values("FETCH:WAV:ADC? (@1)", datatype='h', container=np.array, chunk_size = 200*1024)
            
            # stop timer
            t1 = time.time()
            print(f"read time taken {t1-t0}")
            # save the time it took
            query_times.append(t1-t0)
            
            print(f"len list: {len(s)}")
            print(f"beg list: {s[0:20]}")
            print(f"end list: {s[-20:-1]}")
            
        # print the results
        print(num_samples)
        print(query_times)
        for i in range(len(num_samples)):
            print(f"{num_samples[i]}, {query_times[i]}")

        
    
    # def aquire_one_channel_waveform(self,channel=1):
    #     """
    #     Aquires a waveform for one channel at the next trigger.
    #     
    #     Initiates a measurement at next trigger.
    #     Waits until predicted time has elapsed.
    #     Reads the data for a single channel from the digitizer.
    #     Formerly called 'get_single_channel_waveform'.
    #     """
    #     self.initiate()
    #     channel = str(channel)
    #     if self.params['data_format'] == 'adc16':
    #         self.write("FETCH:WAVeform:ADC? (@"+channel+")")
    #         time.sleep(self.params['num_samples']/self.params['sampling_rate'])
    #         raw_data = self.read()   #(self.params['num_samples']*2+100)
    #         data = np.frombuffer(raw_data[11:-1], dtype=np.int16)
    #     elif self.params['data_format'] == 'float32':
    #         self.write("FETCH:WAVeform:VOLTAGE? (@"+channel+")")
    #         time.sleep(self.params['num_samples']/self.params['sampling_rate'])
    #         raw_data = self.read()   #(self.params['num_samples']*2+100)
    #         data = np.frombuffer(raw_data[11:-1], dtype=np.float32)
    #     return data
    # 
    # def aquire_two_channel_waveform(self):
    #     """
    #     Aquires both waveforms at the next trigger.
    #     
    #     Initiates a measurement at next trigger.
    #     Waits until predicted time has elapsed.
    #     Reads the data for both channels from the digitizer.
    #     Formerly called 'get_two_channel_waveform_instantly'.
    #     """
    #     self.initiate()
    #     if self.params['data_format'] == 'adc16':500
    #         self.write("FETCH:WAVeform:ADC? (@1,2)")
    #         time.sleep(self.params['num_samples']/self.params['sampling_rate'])
    #         raw_data = self.read()
    #         data = np.frombuffer(raw_data[11:-1], dtype=np.int16)
    #     elif self.params['data_format'] == 'float32':
    #         self.write("FETCH:WAVEFORM:VOLTAGE? (@1:2)")
    #         time.sleep(self.params['num_samples']/self.params['sampling_rate']*1.03)
    #         raw_data = self.read()
    #         data = np.frombuffer(raw_data[11:-1], dtype=np.float32)
    #     V1 = data[::2]
    #     V2 = data[1::2]
    #     return V1,V2

    
    # Old functions that may have never been useful
    
    # def clear_errors(self,verbose=False):
    #     err_list = []
    #     for i in range(100):
    #         msg = self.get_error()
    #         if verbose: print (msg)
    #         if ('+0,"No error"').encode() in msg:
    #             break
    #         err_list.append(msg)
    #     if verbose: return '\n'.join(err_list)
    #     else: return True

    #   def reset_frozen_digitizer(self):
    #     try: #If frozen at DTR
    #         V1, V2 = self.get_two_channel_waveform()
    #     except TimeoutError:
    #         print('Digitizer momentarily timed out')
    #     self.write('ABORt')
    #     self.clear_errors()
    #     self.send_reset()

    #   def force_lock_to_ext_clock(self,tries=10):
    #     for i in range(tries):
    #         self.clear_errors()
    #         time.sleep(0.1)
    #         self.write("CONF:ROSC EXT")
    #         if 'EXT'.encode() in self.clock_status(): break
    #     return ('EXT'.encode() in self.clock_status()) 
    
    

# This is untested, but I wanted to see how this inheretance would work
# Instead of address being an ip addr, it is ex: "/dev/dgzr_giraffe"
class DigitizerUSB(Digitizer):

    def open_connection(self):
        """
        Make the connection to the device.
        """
        self.addr_string = self.addr
        print(f"Opening connection to {self.addr_string}")
        self.FILE = os.open(self.addr_string, os.O_RDWR)
        print("Connection opened.")

    def close_connection(self):
        """
        Close the connection to the device.
        """
        return os.close(self.FILE)
    
    # basic routines for writing commands and reading responses
    def write(self, command):
        """
        Write a command to the device.
        """
        os.write(self.FILE, (f"{command}\n").encode('ascii'))

    def read(self, length = int(160e6)):
        """
        Read from the device.
        """
        return os.read(self.FILE, length)
        
    def query(self, command):
        """
        Query the device.
        """
        self.write(command)
        return self.read().decode('ascii').strip()

    def query_binary_values_adc16(self, command):
        """
        Query for a response that will give int16 binary values.
        
        Returns a numpy array with int16 elements.
        """
        self.write(command)
        raw_data = self.read()
        return np.frombuffer(raw_data[11:-1], dtype=np.int16)
        
    def query_binary_values_float32(self, command):
        """
        Query for a response that will give float32 binary values.
        
        Returns a numpy array with float32 elements.
        """
        self.write(command)
        raw_data = self.read()
        return np.frombuffer(raw_data[11:-1], dtype=np.float32)
    

class DigitizerSock(Digitizer):
    """
    For maximum speed, connect to the digitizer using low level socket io.
    """
    # Still not sure why pyvisa isn't this fast. It knows about the headers too.
    
    def open_connection(self):
        """
        Make the connection to the device.
        """
        self.addr_string = self.addr
        print(f"Opening connection to {self.addr_string}")
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_QUICKACK, 1)
        self.sock.settimeout(1.0)
        self.sock.connect((self.addr_string,5025))
        print("Connection opened.")

    def close_connection(self):
        """
        Close the connection to the device.
        """
        return self.sock.close()
    
    # basic routines for writing commands and reading responses
    def write(self, command):
        """
        Write a command to the device.
        """
        self.sock.send((f"{command}\n").encode('ascii'))

    def read(self, length = int(20e6)):
        """
        Read from the device.
        """
        ret = self.sock.recv(length)
        return ret
        
    def query(self, command):
        """
        Query the device.
        """
        self.write(command)
        ret = self.read()
        return ret.decode('ascii').strip()

    def query_binary_values_adc16(self, command):
        """
        Query for a response that will give int16 binary values.
        
        Returns a numpy array with int16 elements.
        """
        self.write(command)
        return np.frombuffer(self.read_binary_values(), dtype=np.int16)
        
    def query_binary_values_float32(self, command):
        """
        Query for a response that will give float32 binary values.
        
        Returns a numpy array with float32 elements.
        """
        self.write(command)
        return np.frombuffer(self.read_binary_values(), dtype=np.float32)
    
    # Interface specific functions for reading and writing
    def read_n_bytes(self, num_bytes):
        raw_data = bytearray()
        while len(raw_data) < num_bytes:
            packet = self.sock.recv(num_bytes - len(raw_data))
            if not packet:
                return None
            raw_data.extend(packet)
        return raw_data
    
    def read_binary_values(self):
        header = self.sock.recv(11)
        #print(header)
        num_bytes = int(header.decode('ascii')[2:])# ignore '#9' part of header
        raw_data = self.read_n_bytes(num_bytes)
        self.sock.recv(1) #the '/n'
        return raw_data


    def test_query_timings(self):
        # Iterate through a set of number of samples and time how long each
        # takes to read from the device.
        # Uncomment only one of the query choices to time that choice.
        
        # Because of it's nature (testing different options for reading from the
        # device), this function should be redefined for each interface.
        
        num_samples = [2e1, 5e1, 1e2, 2e2, 5e2, 1e3, 2e3, 5e3, 1e4, 2e4, 5e4, 1e5, 2e5, 5e5, 1e6]
        
        self.write("CONF:TRIG:SOUR SOFT")
        
        query_times = []
        for n in num_samples:
            print(f"Do {n} sample meas.")
            
            # set the number of samples
            self.write(f"CONF:ACQ:SCO {n}")
            time.sleep(0.1)# being extra careful with timing
            
            # do a meas
            self.write("INIT")
            self.write("TRIG:IMM")
            
            # wait the correct time
            print(f"Wait at least {n/self.params['sampling_rate']} seconds for meas to finish")
            time.sleep(n/self.params['sampling_rate'])
            #time.sleep(3.0)# extra wait time to be sure
            print("Meas time done")
            
            print(self.list_errors())
            
            # start timer
            t0 = time.time()
            
            # vary data type and number of channels
            # single channel (1), int16 values
            s = self.query_binary_values_adc16("FETCH:WAV:ADC? (@1)")
            # single channel (2), int16 values
            #s = self.query_binary_values_adc16("FETCH:WAV:ADC? (@2)")
            # dual channel (1,2), int16 values
            #s = self.query_binary_values_adc16("FETCH:WAV:ADC? (@1,2)")
            # single channel (1), float32 values
            #s = self.query_binary_values_float32("FETCH:WAV:VOLTAGE? (@1)")
            # single channel (2), float32 values
            #s = self.query_binary_values_float32("FETCH:WAV:VOLTAGE? (@2)")
            # dual channel (1,2), float32 values
            #s = self.query_binary_values_float32("FETCH:WAV:VOLTAGE? (@1,2)")
            
            # stop timer
            t1 = time.time()
            print(f"read time taken {t1-t0}")
            # save the time it took
            query_times.append(t1-t0)
            
            print(f"len list: {len(s)}")
            print(f"beg list: {s[0:20]}")
            print(f"end list: {s[-20:-1]}")
            
        # print the results
        print(num_samples)
        print(query_times)
        for i in range(len(num_samples)):
            print(f"{num_samples[i]}, {query_times[i]}")

##
if __name__ == '__main__':
    dg = Digitizer()
    #dg = DigitizerSock()
