
# Acquisition Modes

CS_MODE_SINGLE = 0x1 # Single channel acquisition
CS_MODE_DUAL = 0x2   # Dual channel acquisition
CS_MODE_QUAD = 0x4   # Four channel acquisition
CS_MODE_OCT = 0x8    # Eight channel acquisition
CS_MASKED_MODE = 0x0000000f # Mask to use when determining operating mode

CS_MODE_EXPERT_HISTOGRAM = 0x20  #  Expert Histogram (Cobra PCI only)
CS_MODE_SINGLE_CHANNEL2 = 0x40   #  Capture in Single Channel mode with channel 2 (Cobra & CobraMax PCI-E only)

CS_MODE_POWER_ON = 0x80	         #  Disable power saving mode
CS_MODE_REFERENCE_CLK = 0x400	 #  Use 10 MHz reference clock


# Time stamp constants

TIMESTAMP_GCLK = 0x0        # Use sample clock based frequency for time-stamp counter source
TIMESTAMP_MCLK = 0x1        # Use fixed on-board oscillator for time-stamp counter source
TIMESTAMP_SEG_RESET = 0x0   # Reset time-stamp counter on capture start
TIMESTAMP_FREERUN = 0x10    # Manual reset of time-stamp counter.
TIMESTAMP_DEFAULT = TIMESTAMP_GCLK | TIMESTAMP_FREERUN

# Transfer modes

TxMODE_SLAVE            = 0x80000000 # PCI Slave mode transfer used for troubleshooting
TxMODE_RAWDATA          = 0x40000000 # Transfer data in raw data format with timestamp
TxMODE_DEFAULT          = 0x00
TxMODE_DATA_ANALOGONLY  = 0x00       # Transfer only Analog data.
TxMODE_DATA_FLOAT       = 0x01		 # Transfer data in floating point format
TxMODE_TIMESTAMP        = 0x02       # Transfer time-stamp information
TxMODE_DATA_16          = 0x04       # Transfer all data bits including digital input bits
TxMODE_DATA_ONLYDIGITAL	= 0x08       # Transfer only digital input bits
TxMODE_DATA_32          = 0x10       # Transfer data as 32 bit samples
TxMODE_DATA_FFT			= 0x30       # Transfer data in FFT format. Should be used only with eXpert FFT firmware
TxMODE_DATA_INTERLEAVED	= 0x40       # Transfer data in interleaved format
TxMODE_SEGMENT_TAIL     = 0x80       # Transfer segment tail in raw data format
TxMODE_HISTOGRAM        = 0x100      # Transfer histogram data (Cobra PCI only). Should be use only with Expert Histogram
TxMODE_DATA_64          = 0x200      # Transfer data as 64 bit samples

# Channel index
# Channel index. Indexing starts at 1 and spans the whole CompuScope system.
# Channel index is constant and does not depend on Acquisition mode.

CS_CHAN_1 = 1
CS_CHAN_2 = 2

CS_FILTER_OFF = 0
CS_FILTER_ON  = 1

CS_COUPLING_DC        = 0x1
CS_COUPLING_AC        = 0x2
CS_COUPLING_MASK      = 0x3
CS_DIFFERENTIAL_INPUT = 0x4 # Differential input (default is Single-ended input)
CS_DIRECT_ADC_INPUT   = 0x8

CS_REAL_IMP_1M_OHM = 1000000	# Front end 1 MOhm impedance. Also used to indicate HiZ External trigger impedance
CS_REAL_IMP_50_OHM = 50
CS_REAL_IMP_1K_OHM = 1000

# Input ranges

CS_GAIN_100_V  = 100000 # 100 Volt pk-pk input range
CS_GAIN_40_V   = 40000 # 40 Volt peak-peak input range
CS_GAIN_20_V   = 20000 # 20 Volt peak-peak input range
CS_GAIN_10_V   = 10000 # 10 Volt pk-pk input range
CS_GAIN_5_V    = 5000 # 5 Volt peak-peak input range
CS_GAIN_8_V    = 8000 # 8 Volt peak-peak input range
CS_GAIN_4_V    = 4000 # 4 Volt peak-peak input range
CS_GAIN_3_V    = 3000 # 3 Volt peak-peak input range
CS_GAIN_2_V    = 2000 # 2 Volt peak-peak input range
CS_GAIN_1_V    = 1000 # 1 Volt peak-peak input range
CS_GAIN_800_MV = 800  # 800 milliVolt peak-peak input range
CS_GAIN_500_MV = 500  # 500 milliVolt peak-peak input range
CS_GAIN_400_MV = 400  # 400 milliVolt peak-peak input range
CS_GAIN_200_MV = 200  # 200 milliVolt peak-peak input range
CS_GAIN_100_MV = 100  # 100 milliVolt peak-peak input range
CS_GAIN_50_MV  = 50   # 50 milliVolt peak-peak input range

# Trigger Configuration

CS_TRIG_COND_NEG_SLOPE   = 0 # Trigger on the falling slope of the trigger signal
CS_TRIG_COND_POS_SLOPE   = 1 # Trigger on the rising slope of the signal
CS_TRIG_COND_PULSE_WIDTH = 2
CS_MAX_TRIG_COND         = 3


# Trigger relations
CS_RELATION_OR      = 0 # Boolean OR trigger engine 1 and trigger engine 2
CS_RELATION_AND     = 1 # Boolean AND trigger engine 1 and trigger engine 2

CS_TRIG_ENGINES_DIS = 0 # The specified trigger engine is disabled
CS_TRIG_ENGINES_EN  = 1 # The specified trigger engine is enabled

# Trigger Source

CS_TRIG_SOURCE_DISABLE = 0 # Disable trigger engines. Trigger manually or by timeout
CS_TRIG_SOURCE_CHAN_1  = 1 # Use channel index to specify the channel as trigger source
CS_TRIG_SOURCE_CHAN_2  = 2 # Use channel index to specify the channel as trigger source
CS_TRIG_SOURCE_EXT     = -1 # Use external trigger input as trigger source


# CsSet() CsGet() constants

CS_BOARD_INFO     = 1 # Version information about the CompuScope system
CS_SYSTEM         = 3 # Static information about the CompuScope system
CS_CHANNEL        = 4 # Dynamic configuration of channels
CS_TRIGGER        = 5 # Dynamic configuration of the trigger engines
CS_ACQUISITION    = 6 # Dynamic configuration of the acquisition
CS_PARAMS         = 7 #  All parameters for the card: flash, eeprom, nvram
CS_FIR_CONFIG     = 8 # Configuration parameters for FIR filter firmware. Can be used only with the FIR or Storage Media Expert firmware option.
CS_EXTENDED_BOARD_OPTIONS  = 9  # Query information about 2nd and 3rd base-board FPGA images
CS_TIMESTAMP_TICKFREQUENCY = 10 # Query the timestamp tickcount frequency. It is used for calculation of elapsed time.
CS_CHANNEL_ARRAY = 11 # Configure the channels using the ARRAY_CHANNELCONFIG struct properly allocated
CS_TRIGGER_ARRAY = 12 # Configure the triggers using the ARRAY_TRIGGERCONFIG struct properly allocated
CS_SMT_ENVELOPE_CONFIG  = 13 # Configuration parameters for Envelope filter. Can be used only with the Storage Media Testing firmware option.
CS_SMT_HISTOGRAM_CONFIG = 14 #Configuration parameters for Histogram filter. Can be used only with the Storage Media Testing firmware option.
CS_FFT_CONFIG        = 15 # Configuration parameters for FFT eXpert firmware. Can be used only with the FFT firmware option.
CS_FFTWINDOW_CONFIG  = 16 # Window coefficients for FFT eXpert firmware
CS_MULREC_AVG_COUNT  = 17 # Configuration parameters for eXpert MulRec Averaging firmware
CS_TRIG_OUT_CFG      = 18 # Configuration of the Trigger Out synchronisation. Can be use only with STLP81 CompuScope
CS_GET_SEGMENT_COUNT = 19 # Query the segment count. Can be use on eXpert Gate Acquisition to retrieve the actual segment count once the acquisition is complted.
CS_TRIGGERED_INFO    = 200 # Query for the channel that has the triggered event.
CS_SEGMENTTAIL_SIZE_BYTES = 201 # Query for the segment tail size. The value returned is in bytes
CS_STREAM_SEGMENTDATA_SIZE_SAMPLES = 202 # Query for the segment data size in expert Streaming . The value returned is samples.
CS_STREAM_TOTALDATA_SIZE_BYTES = 203 # Query for the total amount of data in expert Streaming . The value returned is in bytes.
CS_IDENTIFY_LED = 204 # Use with the CsSet(). The "Identify" LED will be flashing for about 5 second. Only supported on some of CompuScope models.

# Modify the capture mode. Some of eXpert functions will work in either Memory or Streaming mode. 
# Use with CsSet(), this paramter is used to change the capture mode to Memory or Streaming mode. Only works on some CompuScope models. 
# The capture mode can be changed after CsDo( ACTION_COMMIT ) or CsDo( ACTION_START ).
# Use with CsGet(), to get the current capture mode.
CS_CAPTURE_MODE = 205

# Modify the Data Pack capture mode. The data can be Unpack or Pack mode. By default data format is unpack (native 8-bit or 16-bit data)
# Use with CsSet(), this paramter is used to change the Data Pack mode for Streaming. Only works on some CompuScope models. 
# The data pack  mode can be changed after CsDo( ACTION_COMMIT ) or CsDo( ACTION_START ).
# Use with CsGet(), to get the current Data Pack mode.
CS_DATAPACKING_MODE = 206

CS_GET_DATAFORMAT_INFO      = 207 # Get different information about data format such as: signed or unsigned, packed or unpacked, 8-bit or 16-bit ...

CS_CURRENT_CONFIGURATION     = 1 # Retrieve data from the configuration  settings from the driver
CS_ACQUISITION_CONFIGURATION = 2 # Retrieve hardware configuration settings from the most recent acquisition
CS_ACQUIRED_CONFIGURATION    = 3 # Retrieve the configuration settings that relates to the acquisition buffer


# CsDo Actions

# Transfers configuration setting values from the drivers to the CompuScope hardware.<BR>
# Incorrect values will not be transferred and an error code will be returned.
ACTION_COMMIT = 1

ACTION_START  = 2 # Starts acquisition
ACTION_FORCE  = 3 # Emulates a trigger event
ACTION_ABORT  = 4 # Aborts an acquisition or a transfer
ACTION_CALIB  = 5 # Invokes CompuScope on-board auto-calibration sequence
ACTION_RESET  = 6 # Resets the CompuScope system to its default configuration. All pending operations will be terminated

# Transfers configuration setting values from the drivers to the CompuScope hardware.<BR>
# Incorrect values will be coerced to valid available values, which will be transferred to the CompuScope system.
# If coercion was required CS_CONFIG_CHANGED is returned
ACTION_COMMIT_COERCE = 7

ACTION_TIMESTAMP_RESET = 8 # Resets the time-stamp counter
ACTION_HISTOGRAM_RESET = 9 # Resets the Histogram counters
ACTION_ENCODER1_COUNT_RESET = 10 # Resets the encoder counter
ACTION_ENCODER2_COUNT_RESET = 11

# Send a RESET command to the CompuScope system to reset hardware to its default state (the state after initialization). All pending operations will be terminated
# Use this parameter with caution. If the PC hardware does not support this feature, it could crash the PC.
ACTION_HARD_RESET = 12


# CsGetStatus defines

ACQ_STATUS_READY        = 0 # Ready for acquisition or data transfer
ACQ_STATUS_WAIT_TRIGGER = 1 # Waiting for trigger event
ACQ_STATUS_TRIGGERED    = 2 # CompuScope system has been triggered but is still busy acquiring
ACQ_STATUS_BUSY_TX      = 3 # Data transfer is in progress
ACQ_STATUS_BUSY_CALIB   = 4 # CompuScope on-board auto-calibration sequence  is in progress


# Board types
# Demo systems have their own board types

CSDEMO8_BOARDTYPE  = 0x0801 # 8 bit demo system
CSDEMO12_BOARDTYPE = 0x0802 # 12 bit demo system
CSDEMO14_BOARDTYPE = 0x0803 # 14 bit demo system
CSDEMO16_BOARDTYPE = 0x0804 # 16 bit demo system
CSDEMO32_BOARDTYPE = 0x0805 # 32 bit demo system
CSDEMO_BT_MASK     = 0x0800
CSDEMO_BT_FIRST_BOARD = CSDEMO8_BOARDTYPE
CSDEMO_BT_LAST_BOARD = CSDEMO32_BOARDTYPE


# Nucleon base compuscopes
CSPCIEx_BOARDTYPE       = 0x2000
CSNUCLEONBASE_BOARDTYPE = CSPCIEx_BOARDTYPE

# Razors board types
CS16x1_BOARDTYPE = 0x20
CS16x2_BOARDTYPE = 0x21
CS14x1_BOARDTYPE = 0x22
CS14x2_BOARDTYPE = 0x23
CS12x1_BOARDTYPE = 0x24
CS12x2_BOARDTYPE = 0x25

CS16xyy_BT_FIRST_BOARD = CS16x1_BOARDTYPE
CS16xyy_LAST_BOARD     = CS12x2_BOARDTYPE
CS16xyy_BASEBOARD      = CS16x1_BOARDTYPE

# Oscar board types
CSE42x0_BOARDTYPE = (0x30 | CSPCIEx_BOARDTYPE)
CSE42x2_BOARDTYPE = (0x31 | CSPCIEx_BOARDTYPE)
CSE42x4_BOARDTYPE = (0x32 | CSPCIEx_BOARDTYPE)
CSE42x7_BOARDTYPE = (0x33 | CSPCIEx_BOARDTYPE)
CSE43x0_BOARDTYPE = (0x34 | CSPCIEx_BOARDTYPE)
CSE43x2_BOARDTYPE = (0x35 | CSPCIEx_BOARDTYPE)
CSE43x4_BOARDTYPE = (0x36 | CSPCIEx_BOARDTYPE)
CSE43x7_BOARDTYPE = (0x37 | CSPCIEx_BOARDTYPE)
CSE44x0_BOARDTYPE = (0x38 | CSPCIEx_BOARDTYPE)
CSE44x2_BOARDTYPE = (0x39 | CSPCIEx_BOARDTYPE)
CSE44x4_BOARDTYPE = (0x3A | CSPCIEx_BOARDTYPE)
CSE44x7_BOARDTYPE = (0x3B | CSPCIEx_BOARDTYPE)

CSE4abc_FIRST_BOARD = CSE42x0_BOARDTYPE
CSE4abc_LAST_BOARD  = CSE44x7_BOARDTYPE
CSE4abc_BASEBOARD   = CSE42x0_BOARDTYPE

# Octopus Board types
CS8220_BOARDTYPE = 0x40
CS8221_BOARDTYPE = 0x41
CS8222_BOARDTYPE = 0x42
CS8223_BOARDTYPE = 0x43
CS8224_BOARDTYPE = 0x44
CS8225_BOARDTYPE = 0x45
CS8226_BOARDTYPE = 0x46
CS8227_BOARDTYPE = 0x47
CS8228_BOARDTYPE = 0x48
CS8229_BOARDTYPE = 0x49
# Board types for 12 bit 2 channel Octopus products

CS822x_BOARDTYPE_MASK = 0x40

CS8240_BOARDTYPE = 0x50
CS8241_BOARDTYPE = 0x51
CS8242_BOARDTYPE = 0x52
CS8243_BOARDTYPE = 0x53
CS8244_BOARDTYPE = 0x54
CS8245_BOARDTYPE = 0x55
CS8246_BOARDTYPE = 0x56
CS8247_BOARDTYPE = 0x57
CS8248_BOARDTYPE = 0x58
CS8249_BOARDTYPE = 0x59
# Board types for 12 bit 4 channel Octopus products

CS824x_BOARDTYPE_MASK = 0x50

CS8280_BOARDTYPE = 0x60
CS8281_BOARDTYPE = 0x61
CS8282_BOARDTYPE = 0x62
CS8283_BOARDTYPE = 0x63
CS8284_BOARDTYPE = 0x64
CS8285_BOARDTYPE = 0x65
CS8286_BOARDTYPE = 0x66
CS8287_BOARDTYPE = 0x67
CS8288_BOARDTYPE = 0x68
CS8289_BOARDTYPE = 0x69
#Board types for 12 bit 8 channel Octopus products

CS828x_BOARDTYPE_MASK = 0x60

CS8320_BOARDTYPE = 0x80
CS8321_BOARDTYPE = 0x81
CS8322_BOARDTYPE = 0x82
CS8323_BOARDTYPE = 0x83
CS8324_BOARDTYPE = 0x84
CS8325_BOARDTYPE = 0x85
CS8326_BOARDTYPE = 0x86
CS8327_BOARDTYPE = 0x87
CS8328_BOARDTYPE = 0x88
CS8329_BOARDTYPE = 0x89
#Board types for 14 bit 2 channel Octopus products

CS832x_BOARDTYPE_MASK = 0x80

CS8340_BOARDTYPE = 0x90
CS8341_BOARDTYPE = 0x91
CS8342_BOARDTYPE = 0x92
CS8343_BOARDTYPE = 0x93
CS8344_BOARDTYPE = 0x94
CS8345_BOARDTYPE = 0x95
CS8346_BOARDTYPE = 0x96
CS8347_BOARDTYPE = 0x97
CS8348_BOARDTYPE = 0x98
CS8349_BOARDTYPE = 0x99
#Board types for 14 bit 4 channel Octopus products

CS834x_BOARDTYPE_MASK = 0x90

CS8380_BOARDTYPE = 0xA0
CS8381_BOARDTYPE = 0xA1
CS8382_BOARDTYPE = 0xA2
CS8383_BOARDTYPE = 0xA3
CS8384_BOARDTYPE = 0xA4
CS8385_BOARDTYPE = 0xA5
CS8386_BOARDTYPE = 0xA6
CS8387_BOARDTYPE = 0xA7
CS8388_BOARDTYPE = 0xA8
CS8389_BOARDTYPE = 0xA9
# Board types for 14 bit 8 channel Octopus products
CS838x_BOARDTYPE_MASK = 0xA0

CS8210_BOARDTYPE = 0xB0
CS8211_BOARDTYPE = 0xB1
CS8212_BOARDTYPE = 0xB2
CS8213_BOARDTYPE = 0xB3
CS8214_BOARDTYPE = 0xB4
CS8215_BOARDTYPE = 0xB5
CS8216_BOARDTYPE = 0xB6
CS8217_BOARDTYPE = 0xB7
CS8218_BOARDTYPE = 0xB8
CS8219_BOARDTYPE = 0xB9
# Board types for 12 bit 1 channel Octopus products
CS821x_BOARDTYPE_MASK = 0xB0

CS8310_BOARDTYPE = 0xC0
CS8311_BOARDTYPE = 0xC1
CS8312_BOARDTYPE = 0xC2
CS8313_BOARDTYPE = 0xC3
CS8314_BOARDTYPE = 0xC4
CS8315_BOARDTYPE = 0xC5
CS8316_BOARDTYPE = 0xC6
CS8317_BOARDTYPE = 0xC7
CS8318_BOARDTYPE = 0xC8
CS8319_BOARDTYPE = 0xC9
# Board types for 14 bit 1 channel Octopus products
CS831x_BOARDTYPE_MASK = 0xC0

CS8410_BOARDTYPE = 0xD0
CS8412_BOARDTYPE = 0xD2
CS8420_BOARDTYPE = 0xD4
CS8422_BOARDTYPE = 0xD6
CS8440_BOARDTYPE = 0xD8
CS8442_BOARDTYPE = 0xDA
CS8480_BOARDTYPE = 0xDC
CS8482_BOARDTYPE = 0xDE
# Board types for 16 bit Octopus products
CS84xx_BOARDTYPE_MASK = 0xD0

CS8_BT_MASK        = 0xD0
CS8_BT_FIRST_BOARD = CS8220_BOARDTYPE
CS8_BT_LAST_BOARD  = CS8482_BOARDTYPE
CS8xxx_BASEBOARD   = CS8_BT_FIRST_BOARD

CS_ZAP_FIRST_BOARD = CS8410_BOARDTYPE
CS_ZAP_LAST_BOARD  = CS8482_BOARDTYPE
CS_ZAP_BASEBOARD   = CS_ZAP_FIRST_BOARD

# Board types for Cobra products
CS22G8_BOARDTYPE      = 0x100
CSxyG8_BOARDTYPE_MASK = 0x100
CS21G8_BOARDTYPE      = 0x101
CS11G8_BOARDTYPE      = 0x102
LAB11G_BOARDTYPE      = 0x103
CSxyG8_FIRST_BOARD    = CS22G8_BOARDTYPE
CSxyG8_LAST_BOARD     = LAB11G_BOARDTYPE

# Board type for Base8
CS_BASE8_BOARDTYPE = 0x400

# Board type for CobraX
CS_COBRAX_BOARDTYPE_MASK = 0x480
CSX11G8_BOARDTYPE = 0x481
CSX21G8_BOARDTYPE = 0x482
CSX22G8_BOARDTYPE = 0x483
CSX13G8_BOARDTYPE = 0x484
CSX23G8_BOARDTYPE = 0x485
CSX14G8_BOARDTYPE = 0x486
CSX_NTS_BOARDTYPE = 0x487
CSX24G8_BOARDTYPE = 0x488
CSEcdG8_FIRST_BOARD	= CSX14G8_BOARDTYPE
CSEcdG8_LAST_BOARD	= CSX24G8_BOARDTYPE

# Board types for JD
CS12500_BOARDTYPE = 0x500
CS121G_BOARDTYPE  = 0x501
CS122G_BOARDTYPE  = 0x502
CS14250_BOARDTYPE = 0x510
CS14500_BOARDTYPE = 0x511
CS141G_BOARDTYPE  = 0x512
CSJD_FIRST_BOARD  = CS12500_BOARDTYPE
CSJD_LAST_BOARD   = CS141G_BOARDTYPE

# Usb compuscopes
CSUSB_BOARDTYPE      = 0x1001
CSUSB_BT_FIRST_BOARD = CSUSB_BOARDTYPE
CSUSB_BT_LAST_BOARD  = CSUSB_BOARDTYPE

# Decade12
CSDECADE123G_BOARDTYPE = 0x600
CSDECADE126G_BOARDTYPE = 0x601
CSDECADE_FIRST_BOARD   = CSDECADE123G_BOARDTYPE
CSDECADE_LAST_BOARD    = CSDECADE126G_BOARDTYPE

# Hexagon
CSHEXAGON_161G4_BOARDTYPE = 0x701
CSHEXAGON_161G2_BOARDTYPE = 0x702
CSHEXAGON_16504_BOARDTYPE = 0x703
CSHEXAGON_16502_BOARDTYPE = 0x704
CSHEXAGON_FIRST_BOARD     = CSHEXAGON_161G4_BOARDTYPE
CSHEXAGON_LAST_BOARD      = CSHEXAGON_16502_BOARDTYPE

# Electron board type - is 'ORed' with the regular board type
FCI_BOARDTYPE = 0x10000

# Default timeout value
CS_TIMEOUT_DISABLE = -1

# Notification events

ACQ_EVENT_TRIGGERED = 0 # Trigger event
ACQ_EVENT_END_BUSY  = 1 # End of acquisition event
ACQ_EVENT_END_TXFER = 2 # End of transfer event
ACQ_EVENT_ALARM     = 3 # Alarm event
NUMBER_ACQ_EVENTS   = 4 # Number of acquisition events

# CAPS_ID   used in CsGetSystemCaps() to identify the dynamic configuration requested
# CAPS_ID  =   MainCapsId | SubCapsId
# 
#   -------------------------------------------------
#   |	MainCapsId		 |		0000				|
#   -------------------------------------------------
#   31                15  14                       0
# 
#   ------------------------------------------------
#   |   0000		     |      SubCapsId	       |
#   ------------------------------------------------
#   31                15  14                       0

#   Depending on CapsID, SubCapsId has different meaning
#   When call CsDrvGetSystemCaps(),
#   CapsID and SunCapsID should always be ORed together
# 
#   SubCapsId for CAPS_INPUT_RANGES:
# 			External trigger  SubCapsId = 0
# 			Channel 1		  SubCapsId = 1
# 			Channel 2		  SubCapsId = 2

#   Make sure lower word should be 0

# Query for available sample rates
# Data are returned as an array of CSSAMPLERATETABLE  structures.
# The successful return value indicates size of the array.
CAPS_SAMPLE_RATES = 0x10000

# Query for available input ranges
# This define should be ORed with the channel index. <BR> Channel index starts with 1 (use 0 to query external trigger capabilities).
# Data are returned as an array of CSRANGETABLE  structures. The successful return value indicates size of the array.
CAPS_INPUT_RANGES = 0x20000

# Query for available impedances
# This define should be ORed with the channel index. Channel index starts with 1 (use 0 to query external trigger capabilities).
# Data are returned as an array of CSIMPEDANCETABLE structures. The successful return value indicates size of the array.
CAPS_IMPEDANCES = 0x30000

# Query for available couplings
# This define should be ORed with the channel index. Channel index starts with 1 (use 0 to query external trigger capabilities).
# Data are returned as an array of CSCOUPLINGTABLE structures. The successful return value indicates size of the array.
CAPS_COUPLINGS = 0x40000

# Query for available capture modes.
# Data are returned as an uInt32 which is a bit mask of all available ACQUISITION_MODES.
CAPS_ACQ_MODES = 0x50000

# Query for available channel terminations
# This define should be ORed with the channel index. Channel index starts with 1 (use 0 to query external trigger capabilities).
# Data are returned as an uInt32 which is a bit mask of all available terminations.
CAPS_TERMINATIONS = 0x60000

# Query for availability of flexible triggering (triggering from any of cards in system)
# Data are returned as an uInt32: 0 - no support for flexible trigger; 1 - full support for flexible trigger; 
# 2 - support flexible trigger on input channels but only one external trigger.
CAPS_FLEXIBLE_TRIGGER = 0x70000

#Query for number of trigger engines per board using. Data are returned as an uInt32.
CAPS_BOARD_TRIGGER_ENGINES = 0x80000

# Query for trigger sources available using. 
# Data are returned as an array of int32 each element signifying a valid trigger source.
# By default Return all trigger sources are returned. This define can be also ORed with the CS_MODE_XXXX 
# to retrieve trigger sources available only for that mode.
CAPS_TRIGGER_SOURCES = 0x90000

# Query for available built-in filters.
# This define should be ORed with the channel index. Channel index starts with 1 (use 0 to query external trigger capabilities).<
# Built-in filters are available only on some CompuScope models. Failure to query means that no built-in filters are available.
# Data are returned as an array of CSFILTERTABLE structures.
CAPS_FILTERS = 0xA0000

# Query for Max Padding for segment or depth using.
# Data are returned as an uInt32 containing the max padding depending on board type.
CAPS_MAX_SEGMENT_PADDING = 0xB0000

# Query for DC Offset adjustment capability.
# No data are passed. The return value determines availability of the feature.
CAPS_DC_OFFSET_ADJUST = 0xC0000

# Query for external synchronisation clock inputs.
# No data are passed. The return value determines availability of the feature.
CAPS_CLK_IN = 0xD0000

# Query for FPGA Boot image  capability.
# No data are passed. The return value determines availability of the feature.
CAPS_BOOTIMAGE0 = 0xE0000

# Query for Aux input/output capability.
CAPS_AUX_CONFIG = 0xF0000

# Query for Aux input/output capability.
CAPS_CLOCK_OUT        = 0x100000
CAPS_TRIG_OUT         = 0x110000
CAPS_TRIG_ENABLE      = 0x120000
CAPS_AUX_OUT          = 0x130000
CAPS_AUX_IN_TIMESTAMP = 0x140000


# Query for the new behavior of the hardware.
# New behavior of harware does not allow to switch expert image on the fly. The system need to
# be power down completetly
CAPS_FWCHANGE_REBOOT = 0x150000

# Query for External Trigger input UniPolar capability.
CAPS_EXT_TRIGGER_UNIPOLAR = 0x160000

# Query for number of trigger engines per channel. Data are returned as an uInt32.
CAPS_TRIG_ENGINES_PER_CHAN = 0x200000


# Query for multiple record capability. No data are passed. The return value determines availability of the feature.
CAPS_MULREC = 0x400000

# Query for trigger resolution. Data are returned as an uInt32.
CAPS_TRIGGER_RES = 0x410000


# Query for minimum external clock rate. Data are returned in Hz as an int64.
CAPS_MIN_EXT_RATE = 0x420000


# Query for external clock skip count. Data are returned as an uInt32.
CAPS_SKIP_COUNT = 0x430000


# Query for maximum external clock rate. Data are returned in Hz as an int64.
CAPS_MAX_EXT_RATE = 0x440000


# Query for CsTransferEx() support. No data are passed. The return value determines availability of the feature.
CAPS_TRANSFER_EX = 0x450000


# Query for the transfer size boundary in Streaming mode. Data are returned as an uInt32.
CAPS_STM_TRANSFER_SIZE_BOUNDARY = 0x460000


# Query for the max segment size in Streaming mode. Data are returned as an int64-.
CAPS_STM_MAX_SEGMENTSIZE = 0x470000


# Query for the capability of capturing data from the channel 2 in single channel.
# No data are passed. The return value determines availability of the feature.
CAPS_SINGLE_CHANNEL2 = 0x480000


# Query for the capability of the Identify LED. The LED will be flashing when the request "Identify" is sent to the card.
# No data are passed. The return value determines availability of the feature.
CAPS_SELF_IDENTIFY = 0x490000

# Query for the capability of the max pretrigger depth.
# No data are passed. The return value determines availability of the feature.
CAPS_MAX_PRE_TRIGGER = 0x4A0000

# Query for the capability of the max stream segment using.
# No data are passed. The return value determines availability of the feature.
CAPS_MAX_STREAM_SEGMENT = 0x4B0000


# Query for the capability of the depth increment using.
# No data are passed. The return value determines availability of the feature.
CAPS_DEPTH_INCREMENT = 0x4C0000


# Query for the capability of the trigger delay increment using.
# No data are passed. The return value determines availability of the feature.
CAPS_TRIGGER_DELAY_INCREMENT = 0x4D0000


CS_NO_FILTER  = 0xFFFFFFFF
CS_NO_EXTTRIG = 0xFFFFFFFF


# DDC  constants
# use CsSet with DDC command.

CS_MODE_NO_DDC     = 0x0
CS_DDC_MODE_ENABLE = 0x1
CS_DDC_MODE_CH1    = 0x1
CS_DDC_MODE_CH2    = 0x2
CS_DDC_DEBUG_MUX   = 0x3
CS_DDC_DEBUG_NCO   = 0x4
CS_DDC_MODE_LAST   = 0x4

# Old and obsolete DDC defined.
CS_DDC_MUX_ENABLE = 0x2

# CsSet with DDC Core Config structure.
CS_DDC_CORE_CONFIG = 300

# CsSet with DDC FIR Config structure.
CS_DDC_FIR_COEF_CONFIG = 301

# CsSet with DDC CFIR Config structure.
CS_DDC_CFIR_COEF_CONFIG = 302

# CsSet with DDC PFIR Config structure.
CS_DDC_PFIR_COEF_CONFIG = 303

# CsSet with DDC FIFO DATA
CS_DDC_WRITE_FIFO_DATA = 305

# CsGet with DDC FIFO DATA
CS_DDC_READ_FIFO_DATA = 306

SIZE_OF_FIR_COEFS         = 96
SIZE_OF_CFIR_COEFS        = 21
SIZE_OF_PFIR_COEFS        = 63
DDC_FILTER_COEFS_MAX_SIZE = SIZE_OF_FIR_COEFS + SIZE_OF_CFIR_COEFS + SIZE_OF_PFIR_COEFS
DDC_CORE_CONFIG_OFFSET    = DDC_FILTER_COEFS_MAX_SIZE


CS_DDC_CONFIG = 400   # CsSet with new DDC Config structure.
CS_DDC_SEND_CMD = 401 # CsSet - DDC Control
CS_DDC_SCALE_OVERFLOW_STATUS = 402 # CsGet - DDC Scale Overflow status

# POSITION ENCODER

# Encoder Channel with Encoder Config structure.
CS_PE_ENABLE  = 1
CS_PE_DISABLE = 0

# CsSet  - Counter Reset
CS_ENCODER1_COUNT_RESET = 300
CS_ENCODER2_COUNT_RESET = 301

# CsSet - Encoder Channel with Encoder Config structure.
CS_ENCODER1_CONFIG = 302
CS_ENCODER2_CONFIG = 303

# CsGet  - Count Value
CS_ENCODER1_COUNT = 304
CS_ENCODER2_COUNT = 305

# Input Type: Step And Direction or Quarature.
CS_PE_INPUT_TYPE_STEPANDDIRECTION = 0
CS_PE_INPUT_TYPE_QUARATURE        = 1

# Encoder Mode: Stamping or Trigger-On-Positon mode.
CS_PE_ENCODER_MODE_STAMP = 0
CS_PE_ENCODER_MODE_TOP   = 1


# OCT (Optical  Coherence Tomography) firmware defines
CS_OCT_ENABLE  = 1
CS_OCT_DISABLE = 0

# OCT phy mode connector.
CS_OCT_MODE0 = 0 # Clock on Chan 1, Sample on Chan 2
CS_OCT_MODE1 = 1 # Clock on Chan 2, Sample on Chan 1

# CsSet/CsGet OCT Config structure.
CS_OCT_CORE_CONFIG = 330
CS_OCT_RECORD_LEN  = 331
CS_OCT_CMD_MODE    = 332

# Expert defines

CS_MODE_USER1 = 0x40000000 # Use alternative firmware image 1
CS_MODE_USER2 = 0x80000000 # Use alternative firmware image 2

CS_MODE_SW_AVERAGING = 0x1000 # Use software averaging acquisition mode. Not available for all CompuScope models

# Base board Expert firmware options
CS_BBOPTIONS_FIR           = 0x0001 # FIR options
CS_BBOPTIONS_AVERAGING     = 0x0002	# Averaging options	
CS_BBOPTIONS_MINMAXDETECT  = 0x0004	# MinMax Detection options
CS_BBOPTIONS_CASCADESTREAM = 0x0008 # MulRec Streaming options
CS_BBOPTIONS_MULREC_AVG    = 0x0010 # Multiple Records Average
CS_BBOPTIONS_SMT           = 0x0020 # Complex option with histogram and FIR

CS_BBOPTIONS_FFT_8K        = 0x0040 # FFT 8192
CS_BBOPTIONS_FFT_4K        = 0x0200 # FFT 4096

CS_BBOPTIONS_MULREC_AVG_TD = 0x0400 # Multiple Records Average with Trigger delay
CS_BBOPTIONS_DDC           = 0x0800 # DDC
CS_BBOPTIONS_OCT           = 0x1000 # OCT
CS_BBOPTIONS_STREAM        = 0x2000 # Stream to analysis or disk
CS_AOPTIONS_HISTOGRAM      = 0x4001 # Histogram

CS_BBOPTIONS_FFTMASK       = CS_BBOPTIONS_FFT_4K | CS_BBOPTIONS_FFT_8K
CS_BBOPTIONS_EXPERT_MASK   = 0xFFFF # OR all options aboved 


CSMV_BBOPTIONS_BIG_TRIGGER = 0x80000000 # Option for memory sizes over 2 Gigasamples

# Limitations of hardware averaging
MAX_HW_AVERAGING_DEPTH      = (0xC000-128) # Max trigger depth in hardware Averaging mode (in samples)
MAX_HW_AVERAGE_SEGMENTCOUNT = 1024         # Max segment count in hardware averaging mode

# Limitations of software averaging
MAX_SW_AVERAGING_SEGMENTSIZE = 512*1024    # Max segment size in Software averaging mode (in samples)
MAX_SW_AVERAGE_SEGMENTCOUNT  = 4096	       # Max segment count in software averaging mode

# Limitation of MinMax detection
MAX_MINMAXDETECT_SEGMENTSIZE  = 0x8FFFFFF  # 28 bits Max segment size in Minmax detection mode (in samples)
MAX_MINMAXDETECT_SEGMENTCOUNT = 0x1FFFFFF  # 25 bits Max segment count in Minmax detection mode

MAX_DISKSTREAM_CHANNELS = 16

# Action Id for use in CsExpertCall()

EXFN_CREATEMINMAXQUEUE     = 1  # MinMaxDetect: Create segment info Minmax queue
EXFN_DESTROYMINMAXQUEUE    = 2  # MinMaxDetect: Destroy segment info Minmax queue
EXFN_GETSEGMENTINFO        = 3  # MinMaxDetect: Get Segment Info
EXFN_CLEARERRORMINMAXQUEUE = 4  # MinMaxDetect: Clear Error on MinMax Internal Queue

EXFN_CASCADESTREAM_CONFIG           = 5  # CascadeStream: Configuration
EXFN_CASCADESTREAM_RELEASE          = 6  # CascadeStream: Release resources 
EXFN_CASCADESTREAM_GETCHANNELDATA   = 7  # CascadeStream: Get Channels Data
EXFN_CASCADESTREAM_CHANNELSDATAREAD = 8  # CascadeStream: Notify driver for channels Data Read
EXFN_RAWMULREC_TRANSFER             = 9  # Raw Nulrec: Save Multiple record data in raw data mode

EXFX_DISK_STREAM_MASK         = 0x60000000
EXFN_DISK_STREAM_INITIALIZE   = 10 | EXFX_DISK_STREAM_MASK  # DiskStream: Initialize the subsystem
EXFN_DISK_STREAM_START        = 11 | EXFX_DISK_STREAM_MASK  # DiskStream: Start capturing and transferring data
EXFN_DISK_STREAM_STATUS       = 12 | EXFX_DISK_STREAM_MASK  # DiskStream: Retrieve whether or not we're finished
EXFN_DISK_STREAM_STOP         = 13 | EXFX_DISK_STREAM_MASK  # DiskStream: Abort any pending captures, transfers or writes
EXFN_DISK_STREAM_CLOSE        = 14 | EXFX_DISK_STREAM_MASK  # DiskStream: Close the subsystem and clean up an allocated resources
EXFN_DISK_STREAM_WRITE_COUNT  = 16 | EXFX_DISK_STREAM_MASK  # DiskStream: Return the number of completed file writes so far
EXFN_DISK_STREAM_ACQ_COUNT    = 15 | EXFX_DISK_STREAM_MASK  # DiskStream: Return the number of acquisitions performed so far
EXFN_DISK_STREAM_ERRORS       = 17 | EXFX_DISK_STREAM_MASK  # DiskStream: Return the last error
EXFN_DISK_STREAM_TIMING_FLAG  = 18 | EXFX_DISK_STREAM_MASK  # DiskStream: Flag to enable timing statistics
EXFN_DISK_STREAM_TIMING_STATS = 19 | EXFX_DISK_STREAM_MASK  # DiskStream: Return the timing statistics, if available

EXFN_STREAM_INIT      = 20  # Streaming config and initialize
EXFN_STREAM_CLEANUP   = 21  # Streaming cleanup resources
EXFN_STREAM_START     = 22  # Start acquisiton in stream mode
EXFN_STREAM_GETSTATUS = 23  # Streaming Get status
EXFN_STREAM_ABORT     = 24  # Streaming Stop or Abort
EXFN_STREAM_TEST1     = 25  # Streaming Stop or Abort
EXFN_STREAM_TEST2     = 26  # Streaming Stop or Abort


# STREAM_STATUS streaming Status

STM_TRANSFER_ERROR_FIFOFULL = 1  # Stream data transfer has been completed success fully

