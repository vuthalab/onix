Process by which we will run experiments in phase with the Pulse Tube.

File: onix/micro/microphone/microphone/microphone.ino
Content: Arduino file to run the Quarto. Applies a 10 Hz low pass IIR filter.
See https://qnimble.com/Quarto/Examples/Filter for how it is implemented.
Samples at 1 MHz on input 1. The command "data" reads out the data, in bytes.
The command "adc_interval" returns the sample time, ASCII formatted.

File: onix/headers/microphone/__init__.py
Content: Simple header to communicate with the Quarto.
Allows you to ask for data and the adc_interval.

File: onix/analysis/microphone.py
Content: Creates the Microphone class which inherits from both the Fitter class
and the Quarto class, as defined in onix/headers/microphone/__init__.py.

The parameter num_periods_fit determines how many periods worth of old
data we should use to fit to. This is 10 by default. 

The parameter num_periods_save determines how many of the old fitted
periods we ought to save. By default this is 100. 

The parameter get_data_time is how often you want to ask the Quarto for data.
You can't ask the Quarto for more than 30,000 data points, so the maximum
get_data_time is 30,000 * adc_interval.

