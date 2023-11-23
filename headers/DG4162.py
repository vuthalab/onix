"""RigolIntruments.py
~~~~~~~~~~~~~~

A collection of classes to perform simple interfaces with oscilloscopes,
function generators, and other instruments purchased from Rigol

Communication is performed with the use of the pyVISA package, which itself
requires either:
 - National Instruments VISA drivers
	(https://pyvisa.readthedocs.io/en/stable/getting_nivisa.html#getting-nivisa)
 - pyVISA-py, with PySerial and PyUSB
 	(https://pyvisa-py.readthedocs.io/en/latest/)


Graham Edge
March 27, 2017
"""

#Internal packages
import time
import os
import random

#External packages
import pyvisa
import serial
import numpy as np
#import pandas as pd
import matplotlib.pyplot as plt

#To Do
# - sort out arbitrary waveforms for the DG1032
# - sort out arbitrary waveforms for the DG4162
# - add more functions:
#		- send software trigger
#		- channel 1 = channel 2
#		- AM, FM, PM, Sweep Modulation
#		- set trigger parameters (rising/falling, INT/EXT/MAN)

#----------------------------------------------------------------------------------
# Some backend USBTMC classes
#----------------------------------------------------------------------------------
class usbtmc:
    """Simple implementation of a USBTMC device driver, in the style of visa.h"""
 
    def __init__(self, device):
        self.device = device
        self.FILE = os.open(device, os.O_RDWR)
 
        # TODO: Test that the file opened
 
    def write(self, command):
        os.write(self.FILE, command);
 
    def read(self, length = 4000):
        return os.read(self.FILE, length)

    def query(self, command, length = 4000):
    	self.write(command)
    	return self.read(length)
 
    def getName(self):
        self.write("*IDN?")
        return self.read(300)
 
    def sendReset(self):
        self.write("*RST")


class DG4162(object):
	'''
	A class for computer control of the Rigol DG4162 Dual Output Function Generator
	
	Author: Graham Edge
	Date: March 24, 2017

	Requires the following packages:
		pyvisa 			(for VISA communication)
		pyvisa-py 		(backend drivers for VISA communication, not needed if NI drivers are installed)
		pyusb			(usb support for pyvisa-py, also not needed if NI drivers are installed)

	An example call to this class would look like:
	
		x = RigolDG4162(ResourceManager, Address)


	where 'rm' is a resource manager class created by pyvisa, and 'address' is a 
	bytestream giving the USB address of the connected generator, as would be generated 
	by pyvisa code of the following form:
	
		rm = pyvisa.ResourceManager('@py') 	#I use '@py' here to connect with the pyvisa-py backend, rather than the NI backend
		ilist = rm.list_resources()


	If the RG4162 is the only instrument connected to the computer, then its address would be:
	
		address = ilist[0]


	and so the device could be connected using:
	
		x = RigolDG4162(rm, ilist[0])
	'''

	def __init__(self, resourceManager, address):
		'''
		Establish communication with the instrument
		'''

		self.resource = resourceManager.open_resource(address)
		try:
			self.idn = self.resource.query('*IDN?')
			print('\nSuccessfully connected to instrument:\n' + self.idn)
		except:
			print('Unable to connect to instrument!')

	def close(self):
		'''
		Close the VISA session
		'''
		self.resource.close()
		
	def ExtBurst(self,channel,nCycl, slope): #function for externally triggered burst
		
		command = ':SOURCE'+str(channel)+':BURS:STATE ON'		#Enable the burst mode
		self.resource.write(command)

		command = ':SOUCE'+str(channel)+':BURS:MODE TRIG' #enable triggering
		self.resource.write(command)

		command = ':SOURCE'+str(channel)+':BURS:TRIG:SOUR EXT'	#External triggering
		self.resource.write(command)
		
		if slope == 'positive':
			command = ':SOURCE'+str(channel)+':BURS:TRIG:SLOP POS' #set positive slope
		elif slope == 'negative':
			command = ':SOURCE'+str(channel)+':BURS:TRIG:SLOP NEG' #set negative slope
		self.resource.write(command)

		command = ':SOURCE'+str(channel)+':BURST:NCYC ' + str(nCycl)	#Set the number of cycles
		self.resource.write(command)
		
	def getTrigSource(self):
		'''
		Returns the trigger source
		'''
		command = 'BURS:TRIG:SOUR?'
		return self.resource.query(command)
		
	def getTrigSlope(self):
		'''
		Returns the trigger slope
		'''
		command = 'BURS:TRIG:SLOP?'
		return self.resource.query(command)
		
	def setLeadTrailMinimum(self, channel):
		"""
		Set the rise and fall times to a minimum. Is probably dependent on the frequency of the waveform
		"""
		command = ':SOUR'+str(channel)+':PULS:TRAN:TRA 0'
		self.resource.write(command)
		
		command = ':SOUR'+str(channel)+':PULS:TRAN:LEAD 0'
		self.resource.write(command)
		
		
	def setPulse(self, channel, highV = 1, lowV = -1, period = 1e-3, duty = 50, delay = 0):
		'''
		Set a square wave with arbitrary high, low values
		'''
		freq = 1.0/period
		ampl = (highV - lowV)/1.0
		offset = (highV + lowV)/2.0
		phase = (delay/period)*360.0

		command = ':SOURCE'+str(channel)+':APPL:PULSE '+str(freq)+','+str(ampl)+','+str(offset)+','+str(phase)
		self.resource.write(command)
		time.sleep(0.05)

		command = ':SOURCE'+str(channel)+':FUNCTION:PULSE:DCYCLE '+str(duty)
		self.resource.write(command)
		time.sleep(0.05)

	def unlock(self):
		'''
		Unlock the font panel keys
		(this only -allows- the user to unlock the keys by pressing "Help" on the front panel)
		'''
		
		self.resource.write(':SYST:KLOC:STATE OFF')
		

	def toggleFrontPanel(self):
		'''
		Lock/unlock the front panel buttons
		
		Note: The front panel buttons always become locked out when connected via USB.
				The KLOCK function either allows or disallows the user from breaking
				local control by pushing the BURST button

				When this option is toggled on, there will be no way to access the front panel
				without closing the USB connection
		'''
		self.resource.write(':SYST:KLOCK: OFF')

	def setFrequency(self, channel, freq, ampl = 1.4, offset = 0, phase = 0):
		'''
		Set the output 'channel' to a sine wave with the given frequency, 
		amplitude, phase, and offset
		'''

		command_string = ':SOURCE'+str(channel)+':APPL:SIN '+str(freq)+','+str(ampl)+','+str(offset)+','+str(phase)
		self.resource.write(command_string)


	def setSineWave(self, channel, freq, ampl = 0.9, offset = 0, phase = 0):

		command = ':SOURCE'+str(channel)+':APPL:SIN '+str(freq)+','+str(ampl)+','+str(offset)+','+str(phase)
		self.resource.write(command)

	def setNCycBurst(self, channel, nCycl = 1, trigSource = 'INT', burstPeriod = 1.0, tDelay = 0, idleLevel = 0):
		''' 
		Turn on the burst mode
		
		Idle level is a number between 0 and 16383 (14 bits, which sets the idle level of the signal between
		bursts to either the min (if idle=0) of the waveform, the max (if idle=16384) , or 
		somewhere in between
		'''

		command = ':SOURCE'+str(channel)+':BURST:NCYC ' + str(nCycl)	#Set the number of cycles
		self.resource.write(command)


		command = ':SOURCE'+str(channel)+':BURST:MODE TRIG'			#Set the burst to occur on trigger
		self.resource.write(command)


		command = ':SOURCE'+str(channel)+':BURST:TRIG:SOURCE '+trigSource	#External triggering
		self.resource.write(command)


		if trigSource == 'INT':
			#Set the period of the internal trigger
			command = ':SOURCE'+str(channel)+':BURST:INT:PER '+str(burstPeriod)	#Set burst period
			self.resource.write(command)


		command = ':SOURCE'+str(channel)+':BURST:TDEL ' + str(tDelay)	#Set the delay
		self.resource.write(command)


		command = ':SOURCE'+str(channel)+':BURST:IDEL ' + str(idleLevel)	#Set the leve between bursts
		self.resource.write(command)


		command = ':SOURCE'+str(channel)+':BURST:STATE ON'		#Enable the burst mode
		self.resource.write(command)

	def SingleBurst(self,channel,nCycl): #function for manually triggered burst
		
		command = ':SOURCE'+str(channel)+':BURST:STATE ON'		#Enable the burst mode
		self.resource.write(command)

		command = ':SOURCE'+str(channel)+':BURST:TRIG:SOURCE MAN'	#External triggering
		self.resource.write(command)

		command = ':SOURCE'+str(channel)+':BURST:NCYC ' + str(nCycl)	#Set the number of cycles
		self.resource.write(command)


	def TurnoffBurst(self,channel):
		command = ':SOURCE'+str(channel)+':BURST:STATE OFF'		#press burst switch once
		self.resource.write(command)

		command = ':SOURCE'+str(channel)+':BURST:STATE OFF'		#press burst switch twice, disable the burst mode
		self.resource.write(command)



	def sendTrigger(self, channel):
		'''Send a software trigger to the specified channel, for burst mode'''
		command = ':SOURCE' + str(channel) + ':BURST:TRIGGER:IMM'
		self.resource.write(command)

	def setFMdev(self,channel,FMdev,trigSource='EXT'):
		#set the FMdev

		command = ':SOURCE' + str(channel) + ':MOD ON'
		self.resource.write(command)
		command = ':SOURCE' + str(channel) + ':MOD:TYP FM'
		self.resource.write(command)
		command = ':SOURCE' + str(channel) + ':MOD:FM '+str(FMdev)
		self.resource.write(command)
		command = ':SOURCE' + str(channel) + ':MOD:FM:SOUR '+trigSource
		self.resource.write(command)
	
	def setModOff(self, channel):
		#turns off MOD setting
		command = ':SOURCE' + str(channel) + ':MOD OFF'
		self.resource.write(command)

	def setSquareWave(self, channel, highV = 1, lowV = -1, period = 1e-3, delay = 0):
		'''
		Set a square wave with arbitrary high, low values
		'''
		freq = 1.0/period
		ampl = (highV - lowV)/1.0
		offset = (highV + lowV)/2.0
		phase = (delay/period)*360.0

		command = ':SOURCE'+str(channel)+':APPL:SQU '+str(freq)+','+str(ampl)+','+str(offset)+','+str(phase)
		self.resource.write(command)

	def setArbitrary(self, channel, samplerate = 200, ampl = 1, offs = 0):
		''' 
		Turn on the arbitrary waveform output of the selected channel, with
		20MSa/s sampling rate (the default), a peak to peak amplitude of 'ampl',
		and an offset of 'offs'

		Does not actually define the arbitrary waveform
		'''
		#Turn on arbitrary output
		command = ':SOURCE'+str(channel)+':FUNC:ARB:SRAT '+str(samplerate)+','+str(ampl)+','+str(offs)
		self.resource.write(command)
		time.sleep(0.5)

		
	def getWaveformDetails(self, channel = 1):
		'''
		Query the details of the current waveform
		'''	
		command = ':SOUR'+str(channel)+':APPL?'
		return self.resource.query(command)

	def getPeriod(self, channel):
		''' read the current period of the specified channel waveform'''
		command = ':SOUR'+str(channel)+':PER?'
		return self.resource.query(command)

	def getFrequency(self, channel):
		''' read the current period of the specified channel waveform'''
		command = ':SOUR'+str(channel)+':FREQ?'
		return self.resource.query(command)

	def getVolatilePoints(self,channel = 1):
		'''Check the number of points in volatile memory'''

		return(self.resource.query(':SOUR'+str(channel)+':DATA:POINTS? VOLATILE'))

	def setVolatilePoints(self,n, channel = 1):
		
		self.resource.write(':SOUR'+str(channel)+':TRACE:DATA:POIN VOLATILE,'+str(n))
		time.sleep(0.1)

	def setVolatileVal(self,n,val, channel = 1):
		'''
		Adds the value 'val' to position n in the volatile memory

		Can be used iteratively to build an arbitrary waveform point by point
		(but this is incredibly tedious!)
		'''
		self.resource.write(':SOUR'+str(channel)+':DATA:VAL VOLATILE,'+str(n)+','+str(val))
		time.sleep(0.015)	#wait times less than 10ms can lead to dropped values

	def loadStoredVolatile(self, channel = 1):

		command = ':DATA:COPY VOL.RAF,VOLATILE'
		print(command)
		self.resource.write(command)


	def loadVolatile(self,t,V, channel = 1, pointRange = 16383):
		'''
		Load an arbitrary waveform defined by the time vector t
			and the voltage vector V into the volatile memory

		Elements of t are timepoints in seconds
		
		Elements of V are voltages in Volts
		'''

		if len(t) != len(V):
			print('Voltage and Time vectors for arbitrary waveform do not match!\n')

		#Determine the appropriate volt scale and offset for the channel
		VMax, VMin = ( V.max(), V.min() )
		VAmpl = (VMax - VMin)
		VOffs = (VMax + VMin)/2.0
		V = 1.0*(V-VMin)/VAmpl			#Voltages rescaled to [0,1]
		
		VAmpl = np.round(VAmpl,3)
		VOffs = np.round(VOffs,3)

		#Rescale voltages into the range [0,16383] and store as a list
		val_list = 	list(np.round(V*pointRange).astype(int))
		
		#Determine the appropriate sampling rate for the channel
		nPoints = len(t)
		dt = t[1]-t[0]
		sRate = int(round(1/dt))
		print('Channel ' + str(channel) + ' Arb Settings:\n' \
			'Sampling Rate \t' + str(sRate) + 'Sa/s\n' \
			'Voltage Scale \t' + str(VAmpl) + 'V\n' \
			'Voltage Offset \t' + str(VOffs) + 'V\n')

		#Limits not set yet, configure them
		self.setArbitrary(channel, samplerate = sRate, ampl = VAmpl, offs = VOffs)
		time.sleep(0.1)

		# Set the number of points for the channel
		self.setVolatilePoints(nPoints, channel)
		time.sleep(0.1)

		#Write the points to the channel one by one
		for num, val in enumerate(val_list, start=1):
			if num%50 == 0:
				print('Loading point {0!s} with value {1!s}'.format(num,val))
			self.setVolatileVal(num,val, channel)

	
	def setStairWaveUp(self,channel,Nstep=7,ptsperstep=32, VoltsPerStep = 0.1,TimePerStep = 0.032):
		'''
		A function that can generate a stair up waveform. ptsperstep is the smaple nuber per each step.
		'''
		#use these commands to set amplitude and period of the wave. :SOUR:FUNC:ARB does not work

		Ampl = VoltsPerStep*Nstep
		command = ':SOURce'+str(channel)+':VOLTage '+str(Ampl)
		self.resource.write(command)

		Period = TimePerStep*Nstep
		command = ':SOURce'+str(channel)+':PERiod '+str(Period)
		self.resource.write(command)


		time.sleep(0.5)
		
		nPoints = Nstep*ptsperstep
		#print nPoints
		self.setVolatilePoints(nPoints, channel)
		time.sleep(0.1)


		#generating the steps (by rewriting the points one by one)
		val = 0
		step = -1
		for i in range(nPoints):

			
			if i%ptsperstep == 0:
				step += 1
				#print 'step',step
				val = int(16384*(float(step)/Nstep))
				#print 'renewing value to ',val

			self.setVolatileVal(i,val, channel)

		self.setArbitrary(1, samplerate = 200, ampl = 1.3, offs = 0)
		
	def setStairWaveUpDown(self,channel,NstepUp=8,ptsperstep=32, VoltsPerStep = 0.1,TimePerStep = 0.032):
		'''
		A function that can generate a stair up waveform followed by a stair down waveform.
		ptsperstep is the smaple nuber per each step.
		NstepUp is the number of steps up including 0.
		'''
		#use these commands to set amplitude and period of the wave. :SOUR:FUNC:ARB does not work
		
		PreMidStep  = NstepUp-1
		
		Nstep = NstepUp+PreMidStep
		#print 'The total steps are ',Nstep

		Ampl = VoltsPerStep*NstepUp
		command = ':SOURce'+str(channel)+':VOLTage:HIGH '+str(Ampl)
		self.resource.write(command)

		command = ':SOURce'+str(channel)+':VOLTage:LOW 0'
		self.resource.write(command)


		Period = TimePerStep*Nstep
		command = ':SOURce'+str(channel)+':PERiod '+str(Period)
		self.resource.write(command)


		time.sleep(0.5)
		
		nPoints = Nstep*ptsperstep
		#print nPoints
		self.setVolatilePoints(nPoints, channel)
		time.sleep(0.1)


		#generating the steps (by rewriting the points one by one)
		val = 0
		step = -1
		for i in range(nPoints):

			if step < PreMidStep:
				if i%ptsperstep == 0:
					step += 1
					#print 'step',step
					val = int(16383*(float(step)/PreMidStep))
					#print 'renewing value to ',val

				self.setVolatileVal(i,val, channel)


			else:
				if i%ptsperstep == 0:
					step += 1
					#print 'step',step
					val = int(16384*(float(Nstep-step)/PreMidStep)-8192/PreMidStep)
					#print 'renewing value to ',val

				self.setVolatileVal(i,val, channel)


		self.setArbitrary(1, samplerate = 200, ampl = 1.3, offs = 0)

	def checkVolatile(self):
		
		command = 'SOURCE1:DATA:CAT?'
		print(self.resource.query(command))
		time.sleep(0.1)	

	def Arbwave(self, WaveFormArray,Npts, channel = 1):

		command = ':SOUR1:APPL:ARB 2'
		self.resource.write(command)
		command = ':SOURCE'+str(channel)+':FUNC:ARB:SRAT '
		self.resource.write(command)
		time.sleep(0.5)

		self.resource.write(':SOUR1:TRACE:DATA:POIN VOLATILE,'+str(Npts))
		time.sleep(0.1)

		WaveFormArrayStr = np.array2string(WaveFormArray,separator=',').replace('[','').replace(']','')

		command = ':SOUR1:DATA VOLATILE,'+WaveFormArrayStr
		self.resource.write(command)

		command = ':OUTP1 ON'
		self.resource.write(command)

	def SyncClockExt(self):
		#this allows to syncrhonize two internal clocks
		command = ':SYSTem:ROSCillator:SOURce EXTernal'
		self.resource.write(command)
		time.sleep(3)
		#print 'Clock of Rigol4162 synchronized to ext'