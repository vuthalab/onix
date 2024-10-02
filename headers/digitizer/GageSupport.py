from __future__ import print_function, division  
# division allows python 2 to do floating point division with / and integer with //
# print_function allows python 3 style print statements
try:
    from configparser import ConfigParser # needed for reading ini files
except ImportError:
    from ConfigParser import ConfigParser  # ver. < 3.0

import sys
import os.path  # to check that file exists
    
from onix.headers.digitizer.GageConstants import (CS_MASKED_MODE, TIMESTAMP_MCLK, TIMESTAMP_FREERUN,
                           CS_COUPLING_DC, CS_COUPLING_AC, CS_TRIG_COND_NEG_SLOPE,
                           CS_TRIG_COND_POS_SLOPE, CS_TRIG_COND_PULSE_WIDTH,
                           CS_TRIG_SOURCE_EXT, CS_TRIG_SOURCE_DISABLE)
import platform

# Code used to determine if python is version 2.x or 3.x
# and if os is 32 bits or 64 bits.  If you know the
# python version and os you can skip all this and just
# import the appropriate version

os_name = platform.system()

if os_name == 'Windows':
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


TYPE_DEC = 0
TYPE_HEX = 1
TYPE_FLOAT = 2
TYPE_SIG = 3
TYPE_BIN = 4
TYPE_BIN_APPEND = 5

INI_FILE_MISSING = -1
PARAMETERS_MISSING = -2

def CalculateChannelIndexIncrement(mode, channel_count, board_count):
    masked_mode = mode & CS_MASKED_MODE
    channels_per_board = channel_count // board_count #integer division
    if masked_mode == 0:
        masked_mode = 1
    channel_increment = channels_per_board // masked_mode
    if channel_increment == 0:
        channel_increment = 1
		
    return channel_increment		
	

def LoadAcquisitionConfiguration(handle, iniFile):
    # Get current values for fields that aren't in the ini file
    acq = PyGage.GetAcquisitionConfig(handle)
    if not isinstance(acq, dict):
        return acq	

    # check if file exists.  The call to ConfigParser() does this
    # as well, but by checking ourselves we can return a flag so
    # we can print out a message that we're using defaults.

    file_exists = os.path.isfile(iniFile)

    # instantiate
    config = ConfigParser()

    # parse existing file
    config.read(iniFile)
    missing_config = False

    if 'Acquisition' in config:
        for key in config['Acquisition']:
            value = config.get('Acquisition', key).lower()
            value = value.lower()
            if key == 'mode':
                if value in ['octal', 'o', '8']:
                    acq['Mode'] = 8 # use constants
                elif value in ['quad', 'q', '32-bit', '32', '4']:
                    acq['Mode'] = 4
                elif value in ['dual', 'd', '16-bit', '16', '2']:
                    acq['Mode'] = 2
                elif value in ['single', 's', '8-bit', '1']:
                    acq['Mode'] = 1
                else: #handle as a number (hex or dec)
                    if value[:2] == '0x':
                        acq['Mode'] = int(value, 16)
                    else:
                        acq['Mode'] = int(value, 10)					
            elif key == 'samplerate':
                acq['SampleRate'] = int(value)  # see if there's 64 bit            			
            elif key == 'depth':
                acq['Depth'] = int(value)
            elif key == 'segmentsize':
                acq['SegmentSize'] = int(value)
            elif key == 'segmentcount':
                acq['SegmentCount'] = int(value)
            elif key == 'triggerholdoff':
                acq['TriggerHoldoff'] = int(value)
            elif key == 'triggertimeout':
                acq['TriggerTimeout'] = int(value)
            elif key == 'triggerdelay':
                acq['TriggerDelay'] = int(value)
            elif key == 'extclk':
                acq['ExtClk'] = int(value)
            elif key == 'extclksampleskip':
                acq['ExtClkSampleSkip'] = int(value)                
            elif key == 'timestampclock':
                if value == 'fixed':
                    acq['TimeStampConfig'] |= TIMESTAMP_MCLK
                else:					
                    acq['TimeStampConfig'] &= ~TIMESTAMP_MCLK                  				
            elif key == 'timestampmode':
                if value == 'free':
                    acq['TimeStampConfig'] |= TIMESTAMP_FREERUN
                else:					
                    acq['TimeStampConfig'] &= ~TIMESTAMP_FREERUN                  				
    else:
        missing_config = True

    if not file_exists:
        status = INI_FILE_MISSING
    elif missing_config:
        status = PARAMETERS_MISSING
    else:
        status = 1

    return acq, status


def LoadChannelConfiguration(handle, channel, iniFile):
    # Get current values for fields that aren't in the ini file
    chan = PyGage.GetChannelConfig(handle, channel)
    if not isinstance(chan, dict):
        return chan	

    # check if file exists.  The call to ConfigParser() does this
    # as well, but by checking ourselves we can return a flag so
    # we can print out a message that we're using defaults.

    file_exists = os.path.isfile(iniFile)
    missing_config = False

    # instantiate
    config = ConfigParser()

    # parse existing file
    config.read(iniFile)

    section = 'Channel' + str(channel)

    if section in config:
        for key in config[section]:
            value = config.get(section, key).lower()
            value = value.lower()			
            if key == 'range':
                chan['InputRange'] = int(value)
            elif key == 'coupling':
                if value == 'dc' or value == '1':
                    chan['Coupling'] = CS_COUPLING_DC
                elif value == 'ac' or value == '2':
                    chan['Coupling'] = CS_COUPLING_AC
            elif key == 'impedance':
                chan['Impedance'] = int(value)
            elif key == 'dcoffset':
                chan['DcOffset'] = int(value)
            elif key == 'filter':
                chan['Filter'] = int(value)
    else:
        missing_config = True

    if not file_exists:
        status = INI_FILE_MISSING
    elif missing_config:
        status = PARAMETERS_MISSING
    else:
        status = 1

    return chan, status


def LoadTriggerConfiguration(handle, trigger, iniFile):	
    # Get current values for fields that aren't in the ini file
    trig = PyGage.GetTriggerConfig(handle, trigger)
    if not isinstance(trig, dict):
        return trig	

    # check if file exists.  The call to ConfigParser() does this
    # as well, but by checking ourselves we can return a flag so
    # we can print out a message that we're using defaults.

    file_exists = os.path.isfile(iniFile)
    missing_config = False

    # instantiate
    config = ConfigParser()

    # parse existing file
    config.read(iniFile)

    section = 'Trigger' + str(trigger)

    if section in config:
        for key in config[section]:
            value = config.get(section, key).lower()	
            value = value.lower()			
            if key == 'condition':
                if value in ['falling', 'negative', '0']:
                    trig['Condition'] = CS_TRIG_COND_NEG_SLOPE
                elif value == 'pulsewidth':
                    trig['Condition'] = CS_TRIG_COND_PULSE_WIDTH
                else:
                    trig['Condition'] = CS_TRIG_COND_POS_SLOPE
            elif key == 'level':
                trig['Level'] = int(value)
            elif key == 'source':
                if value == 'external':
                    trig['Source'] = CS_TRIG_SOURCE_EXT
                elif value == 'disable':
                    trig['Source'] = CS_TRIG_SOURCE_DISABLE
                else:					
                    trig['Source'] = int(value)
            elif key == 'coupling':
                if value == 'ac':
                    trig['ExtCoupling'] = CS_COUPLING_AC
                elif value == 'dc':
                    trig['ExtCoupling'] = CS_COUPLING_DC
                else:
                    trig['ExtCoupling'] = int(value)
            elif key == 'range':
                trig['ExtRange'] = int(value)
            elif key == 'impedance':
                trig['ExtImpedance'] = int(value)
            elif key == 'relation':
                trig['Relation'] = int(value)	
    else:
        missing_config = True

    if not file_exists:
        status = INI_FILE_MISSING
    elif missing_config:
        status = PARAMETERS_MISSING
    else:
        status = 1
                		
    return trig, status

def LoadApplicationConfiguration(iniFile):
    # create a dictionary and fill it with default values

    app = {}
    app['StartPosition'] = 0
    app['TransferLength'] = 4096
    app['SegmentStart'] = 1
    app['SegmentCount'] = 1
    app['PageSize'] = 32768
    app['SaveFileName'] = 'GAGE_FILE'
    app['SaveFileFormat'] = TYPE_DEC

    # check if file exists.  The call to ConfigParser() does this
    # as well, but by checking ourselves we can return a flag so
    # we can print out a message that we're using defaults.

    file_exists = os.path.isfile(iniFile)
    missing_config = False    
	
    config = ConfigParser()

    # parse existing file
    config.read(iniFile)
    section = 'Application'
	
    if section in config:
        for key in config[section]:
            value = config.get(section, key).lower()	
            if key == 'startposition':	
                app['StartPosition'] = int(value)
            elif key == 'transferlength':
                app['TransferLength'] = int(value)
            elif key == 'segmentstart':
                app['SegmentStart'] = int(value)
            elif key == 'segmentcount':
                app['SegmentCount'] = int(value)
            elif key == 'pagesize':
                app['PageSize'] = int(value)
            elif key == 'savefilename':
                value = config.get(section, key) # get original name, not lower case
                app['SaveFileName'] = value  
            elif key == 'savefileformat':
                if value == 'type_dec':
                    app['SaveFileFormat'] = TYPE_DEC
                elif value == 'type_hex':	
                    app['SaveFileFormat'] = TYPE_HEX				
                elif value == 'type_float':	
                    app['SaveFileFormat'] = TYPE_FLOAT	
                elif value == 'type_sig':	
                    app['SaveFileFormat'] = TYPE_SIG	
                elif value == 'type_bin':	
                    app['SaveFileFormat'] = TYPE_BIN	                    
                else: # assume it's a number
                    app['SaveFileFormat'] = int(value)
    else:
        missing_config = True

    if not file_exists:
        status = INI_FILE_MISSING
    elif missing_config:
        status = PARAMETERS_MISSING
    else:
        status = 1                    
					
    return app, status				
    
    
def CreateSigHeader(channel, stHeader):
    head = {}
   
    # Set defaults and then check that the key is there like above
    # if something is missing the library will use defaults
    for key in stHeader:
        value = key.lower()
        if value == 'samplerate':
            head['SampleRate'] = stHeader['SampleRate']
        elif value == 'start':
            head['RecordStart'] = stHeader['Start']
        elif value == 'length':
            head['RecordLength'] = stHeader['Length']
        elif value == 'recordcount':
            head['RecordCount'] = stHeader['SegmentCount']
        elif value == 'samplebits':
            head['SampleBits'] = stHeader['SampleBits']
        elif value == 'samplesize':
            head['SampleSize'] = stHeader['SampleSize']
        elif value == 'sampleoffset':
            head['SampleOffset'] = stHeader['SampleOffset']
        elif value == 'sampleres':
            head['SampleRes'] = stHeader['SampleRes']
        elif value == 'channel':
            head['Channel'] = channel
        elif value == 'inputrange':
            head['InputRange'] = stHeader['InputRange']
        elif value == 'dcoffset':
            head['DcOffset'] = stHeader['DcOffset']
        elif value == 'timestamp':
            timestamp = {}
            for key in stHeader['TimeStamp']:
                val = key.lower()
                if val == 'hour':
                    timestamp['Hour'] = stHeader['TimeStamp']['Hour']
                elif val == 'minute':
                    timestamp['Minute'] = stHeader['TimeStamp']['Minute']
                elif val == 'second':
                    timestamp['Second'] = stHeader['TimeStamp']['Second']
                elif val == 'point1second':
                    timestamp['Point1Second'] = stHeader['TimeStamp']['Point1Second']
            head['TimeStamp'] = timestamp

    sig_header = PyGage.ConvertToSigHeader(head, "GageFile", "Ch " + str(channel))
    return sig_header    
    
    
def CreateAsciiHeader(stHeader):
    header = []
    header.append("----------------------")
    for k,v in stHeader.items():
        key = k.lower()
        if key == 'samplerate':
            st = 'Sample Rate\t=\t' + str(v)
            header.append(st)        
        elif key == 'start':
            st = 'Start Address\t=\t' + str(v)
            header.append(st)
        elif key == 'length':
            st = 'Data Length\t=\t' + str(v)
            header.append(st)        
        elif key == 'samplesize':
            st = 'Sample Size\t=\t' + str(v)
            header.append(st)                    
        elif key == 'samplebits':
            st = 'Sample Bits\t=\t' + str(v)
            header.append(st)   
        elif key == 'sampleres':
            st = 'Sample Res\t=\t' + str(v)
            header.append(st)                                      
        elif key == 'sampleoffset':
            st = 'Sample Offset\t=\t' + str(v)
            header.append(st)
        elif key == 'inputrange':
            st = 'Input Range\t=\t' + str(v)
            header.append(st)                            
        elif key == 'dcoffset':
            st = 'DC Offset\t=\t' + str(v)
            header.append(st)             
        elif key == 'segmentcount':
            st = 'Segment Count\t=\t' + str(v)
            header.append(st)                  
        elif key == 'segmentnumber':
            st = 'Segment Number\t=\t' + str(v)
            header.append(st)                          
        elif key == 'timestamp':
            st = 'TimeStamp\t=\t' + str(v)
            header.append(st)
    header.append("----------------------")            
    return header
            
    
def SaveSigFile(filename, channel, buffer, stHeader):
    sig_header = CreateSigHeader(channel, stHeader)
    try:
        f = open(filename, 'wb') # check for errors
        try:
            sig_header.tofile(f)
            buffer.tofile(f) # may have to check sample bits and save accordingly
        finally:
            f.close()
            return 1
    except IOError:
        return filename

def SaveBinaryFile(filename, buffer, bits):
    try:
        f = open(filename, 'wb') # check for errors or exceptions
        try:
            buffer.tofile(f)
        finally:
            f.close()
            return 1
    except IOError:
        return filename

def SaveDecimalFile(filename, buffer, stHeader):
    try:
        f = open(filename, 'w')
        try:
            header = CreateAsciiHeader(stHeader)
            for st in header:
                print(st, file=f)
            for i in buffer:
                print(i, file=f) # don't seem to need str(i)
        finally:
            f.close()
            return 1
    except IOError:
        return filename
    
def SaveHexFile(filename, buffer, stHeader):
    try:
        f = open(filename, 'w')
        # write out header
        header = CreateAsciiHeader(stHeader)
        try:
            for st in header:
                print(st, file=f)

            for i in buffer:
                print(format(i, '#09x'), file=f) # don't seem to need str(i)
        finally:
            f.close()
            return 1
    except IOError:
        return filename

    
def SaveVoltageFile(filename, buffer, stHeader):
    try:
        f = open(filename, 'w')
        # write out header

        header = CreateAsciiHeader(stHeader)
        try:
            for st in header:
                print(st, file=f)
        
            scale_factor = stHeader['InputRange'] / 2000 
            offset = stHeader['DcOffset'] / 1000
#           l = [(((stHeader['SampleOffset'] - x) / stHeader['SampleRes']) * scale_factor) + offset for x in buffer.tolist()]

            # map seems to be at least an order of magnitude faster than list comprehension for this and 190 times faster
            # than using a for loop on the buffer
            data = map(lambda x:(((stHeader['SampleOffset'] - x) / stHeader['SampleRes']) * scale_factor) + offset, buffer.tolist())

            for i in data:
                print("{:02.6f}".format(i), sep='\n', file=f)
        finally:
            f.close()
            return 1
    except IOError:
        return filename
     

def SaveFile(filename, channel, buffer, format, stHeader):
    if format == TYPE_SIG:
        return SaveSigFile(filename, channel, buffer, stHeader)
    elif format == TYPE_BIN:
        return SaveBinaryFile(filename, buffer, stHeader['SampleBits']) # straight binary, might need header for sample bits
    elif format == TYPE_DEC:
        return SaveDecimalFile(filename, buffer, stHeader) # ascii decimal values
    elif format == TYPE_HEX:
        return SaveHexFile(filename, buffer, stHeader)  # ascii hex values
    elif format == TYPE_FLOAT:
        return SaveVoltageFile(filename, buffer, stHeader)  # ascii voltages
    else:
        return SaveBinaryFile(filename, buffer, stHeader) # default - or return error
        

""" code after this point was just used for testing

def Initialize():
    status = PyGage.Initialize()
    if status < 0:
        return status
    else:
        handle = PyGage.GetSystem(0, 0, 0, 0)
        if (status < 0):
            return status
        return handle
        

def main():
    handle = Initialize()
    if handle < 0:
        # get error string
        print("Error: ", handle)
        raise SystemExit
        
    acq, sts = LoadAcquisitionConfiguration(handle, "Acquire.ini")
    for i, j in acq[0].items():
        print (i, j)
		
    print()	
    chan, sts = LoadChannelConfiguration(handle, 1, "Acquire.ini")
    if isinstance(chan, dict) and chan:
        for i, j in chan.items():
            print (i, j)
        print()	    	
        print()	
    chan, sts = LoadChannelConfiguration(handle, 2, "Acquire.ini")
    if isinstance(chan, dict) and chan:
        for i, j in chan.items():
            print (i, j)
        print()		
		
    trig, sts = LoadTriggerConfiguration(handle, 1, "Acquire.ini")
    if isinstance(trig, dict) and trig:
        for i, j in trig.items():
            print (i, j)
        print()		
		
    PyGage.FreeSystem(handle)
    
 
if __name__ == '__main__':
    main()
"""
