#Internal packages
import time
import os
import random

#External packages
#import visa
import serial
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

class RigolDS1102(object):
    '''
    A class for computer control of the Rigol DS1102 dual channel oscilloscope

    Since there is a known issue with USB connectios on this instrument, it seems
        difficult to connect to the scope using the pyvisa-py backend

    Instead, pyvisa working with the National Instruments VISA backend seems to be OK

    On 64bit Linux where NI drivers are unavailable, connections can be made using
        USBTMC protocol directly rather than going through the VISA interface
    '''

    def __init__(self, resourceManager = [], address = '', path = '/dev/Scope'):
        '''
        Establish communication with the instrument

        If using the resource manager, the address is a bytestream as returned byimport os
        homedir = '/data/vuthalab/'

        os.chdir(homedir+"/code/IonTrap/IonTrap_Control//Experiment Control")
        from CryogenicIons_SetupCode import *
            pyvisa's list_resources() command

        If using USBTMC, then address is ignored and connection is made with 'path,
            the location of the usbtmc file as a string (e.g. '/dev/usbtmc0')
        '''  
        #Using the USBTMC protocol for connection
        #self.resource = usbtmc(path)
        self.path = path
        self.FILE = os.open(path, os.O_RDWR)

        try:
            self.name = self.getName()
            print('\nSuccessfully connected via USBTMC to Rigol Scope:\n' + self.name)
        except:
            print('Unable to connect to Oscilloscope via USBTMC!')

        self.verbose= False

        self.get_scales()
        os.write(self.FILE, (":key:lock disable"+"\n").encode())
    #Define commends for reading and writing over USBTMC
    def write(self, command):
        """
        Send an arbitrary command directly to the scope
        """
        os.write(self.FILE, (command+"\n").encode())
        #self.resource.write(command)  
    def read(self, nRead):
        """Read an arbitrary amount of data directly from the scope"""
        return os.read(self.FILE, nRead)
        #return self.resource.read(nRead)

    def query(self, command, nRead = 200):
        '''A query command to write, and subsequently read specified number of bits'''
        self.write(command)
        return self.read(int(nRead)).decode()

    def getName(self):
        self.write("*IDN?")
        time.sleep(0.5)
        return self.read(3000).decode('utf-8')

    def unlockScope(self):
        self.write(":KEY:FORCE")

    def get_scales(self):
        self.write(":CHAN1:SCAL?") # Get the voltage scale
        self.voltscale1 = float(self.read(20)) # And the voltage offset

        self.write(":CHAN1:OFFS?")
        self.voltoffset1 = float(self.read(20))

        self.write(":CHAN2:SCAL?")
        self.voltscale2 = float(self.read(20))

        self.write(":CHAN2:OFFS?")
        self.voltoffset2 = float(self.read(20))
    def scope_bits_to_volts(self,bits,channel):
        if channel==1:
            voltscale = self.voltscale1
            voltoffset = self.voltoffset1
        elif channel==2:
            voltscale = self.voltscale2
            voltoffset = self.voltoffset2

        decoded_bits = np.frombuffer(bits, 'B')
        volts = decoded_bits * -1 + 255 # First invert the data
        volts = (volts - 130.0 - voltoffset/voltscale*25) / 25 * voltscale

        return volts
    def grab_instant_values(self):
        self.write(":WAV:DATA? CHAN1")
        rawdata1 = self.read(11)
        data1 = self.scope_bits_to_volts(rawdata1,1)
        chan1 = data1[-1] #for some reason first 10 points are garbage

        self.write(":WAV:DATA? CHAN2")
        rawdata2 = self.read(11)
        data2 = self.scope_bits_to_volts(rawdata2,2)
        chan2 = data2[-1] #for some reason first 10 points are garbage

        return chan1,chan2

    def readTrace(self, channel):
        '''Read the data from the specified channel'''
        command = ':WAV:DATA? CHAN' + str(channel)
        self.write(command)        #read waveform data
        #rawdata = self.resource.read(524288 + 10)
        rawdata = self.read(600 + 10)
        data = np.frombuffer(rawdata, 'B')[10:]                #disregard first 10 bits

        if self.verbose:
            print('Read ' + str(len(data)) + ' data points from Channel ' + str(channel) + '.\n')

        return data

    def readTrace(self, channel):
        '''Read the data from the specified channel'''
        command = ':WAV:DATA? CHAN' + str(channel)
        self.write(command)        #read waveform data
        #rawdata = self.resource.read(524288 + 10)
        rawdata = self.read(524288 + 10)
        data = np.frombuffer(rawdata, 'B')[10:]                #disregard first 10 bits

        if self.verbose:
            print('Read ' + str(len(data)) + ' data points from Channel ' + str(channel) + '.\n')

        return data




    def ReadScope(self,AcqAve=False,AveSamples=16):


        self.write(":key:force")
        self.write(":key:lock disable")      # Allows the panel keys on the scope to be used
        if AcqAve:
            self.write(":acquire:type average")
            self.write(":acquire:averages "+str(AveSamples))
        else:
            self.write(":acquire:type normal")
            self.write(":acquire:memdepth long")
            self.write(":acquire:mode EQUAL_TIME")

        #self.write(':WAV:POIN:MODE NORM')
        # Get the timescale and offset
        timescale = float(self.query(":TIM:SCAL?"))
        timeoffset = float(self.query(":TIM:OFFS?"))

        # Voltage scales and offsets
        voltscale1 = float(self.query(":CHAN1:SCAL?"))
        voltoffset1 = float(self.query(":CHAN1:OFFS?"))
        voltscale2 = float(self.query(":CHAN2:SCAL?"))
        voltoffset2 = float(self.query(":CHAN2:OFFS?"))

        # Acquire voltage data for both channels
        #self.write(":WAV:FORM ASC")

        #self.encoding = "latin-1"
        #rawdata1 = map(ord, self.query(":WAV:DATA? CHAN1"))[10:]
        #rawdata2 = map(ord, self.query(":WAV:DATA? CHAN2"))[10:]

        rawdata1 = self.readTrace(1)
        #time.sleep(0.1)
        rawdata2 = self.readTrace(2)
        #time.sleep(0.1)
        # Print sampling rate

        self.write(":RUN")


        # Close scope communication
        self.write(":KEY:FORCE")

        # Process raw data
        V1 = np.asarray(rawdata1)
        V2 = np.asarray(rawdata2)
        #t = np.arange(0,len(V1)*dt,dt)
        t = np.linspace(timeoffset - 6 * timescale, timeoffset + 6 * timescale, num=len(V1))

        # Voltage conversion mumbo-jumbo
        # See: http://www.righto.com/2013/07/rigol-oscilloscope-hacks-with-python.html
        V1 = V1 * -1 +255
        V1 = (V1-130-voltoffset1/voltscale1*25)/25 * voltscale1

        V2 = V2 * -1 +255
        V2 = (V2-130-voltoffset2/voltscale2*25)/25 * voltscale2

        return np.array([t,V1,V2])


    def fnPlotScope(self,data,Option="CH1",PlotTitle="",CH1Label="",CH2Label="",filename=""):
        V1=data[1,:]
        V2=data[2,:]
        t =data[0,:]

        # See if we should use a different time axis
        if (t[-1] < 1e-6):
            t = t * 1e9
            tUnit = "nS"
        elif (t[-1] < 1e-3):
            t = t * 1e6
            tUnit = "uS"
        elif (t[-1] < 1):
            t = t * 1e3
            tUnit = "mS"
        else:
            tUnit = "S"

        # See if we should use a different V1 axis
        minV1 = abs(np.min(V1))*2
        if (minV1 < 1e-3):
            V1 = V1 * 1e6
            V1Unit = "uV"
        elif (minV1 < 1):
            V1 = V1 * 1e3
            V1Unit = "mV"
        else:
            V1Unit = "V"

        # See if we should use a different V1 axis
        minV2 = abs(np.min(V2))*2
        if (minV2 < 1e-3):
            V2 = V2 * 1e6
            V2Unit = "uV"
        elif (minV2 < 1):
            V2 = V2 * 1e3
            V2Unit = "mV"
        else:
            V2Unit = "V"

        # Labels for Channels
        if len(CH1Label)==0:
            ch1_name = "Channel 1"
        else:
            ch1_name = CH1Label

        if len(CH2Label)==0:
            ch2_name = "Channel 2"
        else:
            ch2_name = CH2Label

        # Plot title
        if len(PlotTitle)==0:
            pTitle  = "Scope Trace"
        else:
            pTitle  = PlotTitle

        if Option=="BOTH":
            fig2 = plt.figure()
            ax = fig2.add_subplot(111)
            ln1=ax.plot(t,V1,lw=2,color='r',label = 'C1-'+ch1_name)
            ax.set_ylabel(ch1_name + " Voltage (Red) (" + V1Unit + ")")
            ax.set_xlabel("Time (" + tUnit + ")")

            ax2 = ax.twinx()
            ln2 = ax2.plot(t,V2,lw=2,color='b',label = 'C2-'+ch2_name)
            ax2.set_ylabel(ch2_name + " Voltage (Blue) (" + V2Unit + ")")
    #        if voltscale1==voltscale2:
    #            [p1,p2] = ax.get_ylim()
    #            [q1,q2] = ax2.get_ylim()
    #            ax2.set_ylim(min([p1,p2,q1,q2]),max([p1,p2,q1,q2]))


            lns = ln1+ln2
            labs = [l.get_label() for l in lns]
            ax.legend(lns, labs, loc=3)
            ax.set_title(pTitle)
            ax.xaxis.grid(which='major')
            ax.xaxis.grid(b=True, which='minor', color='r', linestyle='--')
            plt.show()

            # Save the files
            if len(filename)>0:
                fig2.savefig(filename+'.png')
                fig2.savefig(filename+'.pdf')
                np.save(filename,[t,V1,V2],True,True)

        elif Option=="CH1":
            fig2 = plt.figure()
            ax = fig2.add_subplot(111)
            ln1=ax.plot(t,V1,lw=2,color='r',label = 'Channel 1')
            ax.set_ylabel(ch1_name + " Voltage (Red) (" + V1Unit + ")")
            ax.set_xlabel("Time (" + tUnit + ")")

            lns = ln1
            labs = [l.get_label() for l in lns]
            ax.legend(lns, labs, loc=4)
            ax.set_title(pTitle)
            plt.show()

            # Save the files
            if len(filename)>0:
                fig2.savefig(filename+'.png')
                fig2.savefig(filename+'.pdf')
                np.save(filename,[t,V1,V2],True,True)


        elif Option=="CH2":
            fig2 = plt.figure()
            ax = fig2.add_subplot(111)
            ln1=ax.plot(t,V2,lw=2,color='r',label = 'C2-'+ch2_name)
            ax.set_ylabel(ch2_name + " Voltage (Red) (" + V2Unit + ")")
            ax.set_xlabel("Time (" + tUnit + ")")

            lns = ln1
            labs = [l.get_label() for l in lns]
            ax.legend(lns, labs, loc=4)
            ax.set_title(pTitle)
            plt.show()

            # Save the files
            if len(filename)>0:
                fig2.savefig(filename+'.png')
                fig2.savefig(filename+'.pdf')
                np.save(filename,[t,V1,V2],True,True)
        else:
            print ("Option not recognized. Value has to be CH1, CH2 or BOTH")
            
            
    def quick_plot(self):
        data = self.ReadScope()
        
        fig = plt.figure()
        plt.plot(data[0],data[1],label="Channel 1")
        plt.plot(data[0],data[2],label="Channel 2")
        
        plt.show()
        
        
        
if __name__=='__main__':        
    scope = RigolDS1102(path='/dev/usbtmc1')
    scope.quick_plot()

##
"""
    scope.quick_plot()

    data = scope.ReadScope()
    
    save_folder = '/home/labuser/Insync/electric.atoms@gmail.com/GoogleDrive/calcium/data/mot/mot_number_v_chopper/function_of_duty_cycle'
    save_folder = '/home/labuser/Insync/electric.atoms@gmail.com/GoogleDrive/calcium/data/cavity_423'
    
    os.chdir(save_folder)
    fname = 'transmission'
    #np.savetxt('%s.txt'%fname,data)    

    #load_data = np.loadtxt('%s.txt'%fname)

"""