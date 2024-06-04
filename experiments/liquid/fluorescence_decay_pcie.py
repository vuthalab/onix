import time
import os
import numpy as np
import traceback


# os.chdir("/home/onix/Documents/code")
# os.environ["DATAFOLDER"] = "/home/onix/Documents/data"

#os.environ["DATAFOLDER"] = "/home/icarus/Documents/data"

from onix.data_tools import save_experiment_data
from onix.units import ureg

from onix.headers.pcie_digitizer.pcie_digitizer import Digitizer
from onix.headers.wavemeter.wavemeter import WM
from onix.headers.awg.M4i6622 import M4i6622
from onix.sequences.sequence import Sequence, Segment, AWGSinePulse, TTLPulses

# dg = DigitizerVisa("192.168.0.125")
# dg_channels = [1, 2]


import contextlib
import io
import sys

try:
    m4i  # type: ignore
    print("m4i is already defined.")
except Exception:
    try:
        m4i = M4i6622()
    except Exception as e:
        m4i = None
        print("m4i is not defined with error:")
        print(traceback.format_exc())

try:
    wm # type: ignore
    print("WM is already defined")
except Exception:
    try:
        wm = WM()
    except Exception as e:
        wm = None
        print("wm is not defined with error:")
        print(traceback.format_exc())


def wavemeter_frequency():
    freq = wm.read_frequency(5)
    if isinstance(freq, str):
        return -1
    return freq

os.chdir("/home/icarus/Documents/code/onix/experiments/liquid")
from VALOControlUnit import *
valo = VALOControlUnit()
## Function def
def get_etalon_temp():
    return valo.get_TEC_temperature(5)

def set_etalon_temp(temp):
    return valo.set_TEC_temperature_setpoint(5, temp)

def etalon_scan(start_temp, end_temp, step_size, time_box, tolerance):
    i=0
    temps = np.arange(start_temp, end_temp, step_size)
    temps = np.concatenate([temps, np.flip(temps)])
    print(temps)
    try:
        while True:
            if np.abs(get_etalon_temp()-temps[i]) > tolerance:
                set_etalon_temp(temps[i])
                print(f"Waiting for etalon to get to temp of {temps[i]}. It's at {get_etalon_temp()}")
                time.sleep(5)
                continue
            else:
                time.sleep(5)
                capture_sample()
                set_etalon_temp(temps[i])
                print("setting temp to", temps[i])
                i+=1
                if i > len(temps)-1:
                    break
    except KeyboardInterrupt:
        return "interrupt"



## experiment parameters
excitation_aom_channel = 1
excitation_aom_frequency = 78 * ureg.MHz
excitation_aom_amplitude = 2800
excitation_time = 0.5 * ureg.ms
excitation_delay = 10 * ureg.us

test_aom_channel = 1
test_aom_frequency = 78 * ureg.MHz
test_aom_amplitude = 500 #stay below 1k
test_time = 500 * ureg.us

pmt_gate_ttl_channel = 2  # also used to trigger the digitizer.
measurement_time = 8 * ureg.ms + excitation_time

repeats =500
time_between_repeat = measurement_time.to("s").magnitude
sampling_rate = 1e6


## setup sequence
sequence = Sequence()

segment_test = Segment("test")
offset = 100 * ureg.us
ttl_gate = TTLPulses([[0, offset]]) # ttl 0-100us
segment_test.add_ttl_function(pmt_gate_ttl_channel, ttl_gate)
pulse_test = AWGSinePulse( # awg 210 us - 220 us
    frequency=test_aom_frequency,
    amplitude=test_aom_amplitude,
    start_time=offset*2+excitation_delay,
    end_time=offset*2+excitation_delay+test_time,
)
segment_test.add_awg_function(excitation_aom_channel, pulse_test)
segment_test._duration = segment_test.duration + offset
sequence.add_segment(segment_test)

segment_excitation = Segment("excite")
pulse_excitation = AWGSinePulse( # awg 10 us - 5ms
    frequency=excitation_aom_frequency,
    amplitude=excitation_aom_amplitude,
    start_time=excitation_delay,
    end_time=excitation_delay+excitation_time,
) # ttl 5 ms + 20us - 12 ms + 20us
segment_excitation.add_awg_function(excitation_aom_channel, pulse_excitation)
ttl_gate = TTLPulses([[0, 2 * excitation_delay + excitation_time]])
segment_excitation.add_ttl_function(pmt_gate_ttl_channel, ttl_gate)
sequence.add_segment(segment_excitation)

sequence.setup_sequence([("test", 1), ("excite", 1)])



## setup the awg and digitizer
m4i.setup_sequence(sequence)

# dg.configure_acquisition(
#     sample_rate=sampling_rate,
#     samples_per_record=int(measurement_time.to("s").magnitude * sampling_rate),
#     num_records=repeats,
# )
# dg.configure_channels(channels=[1], voltage_range=2)
# dg.set_trigger_source_external()
# dg.set_arm(triggers_per_arm=repeats)

try:
    dg
    print("dg is already defined.")
except Exception:
    dg = Digitizer()


duration = measurement_time.to("s").magnitude
dg.set_acquisition_config(
    num_channels=2,
    sample_rate=sampling_rate,
    segment_size=int(duration * sampling_rate),
    segment_count=repeats,
)

dg.set_channel_config(channel=1, range=2, high_impedance=False) #2 for normalizer, 1 for fluorescence
dg.set_channel_config(channel=2, range=5, high_impedance=True)

dg.set_trigger_source_edge()
dg.write_configs_to_device()
m4i.set_sine_output(excitation_aom_channel, excitation_aom_frequency, excitation_aom_amplitude)
## new experiment function
def prepare_new_temp(temp, tolerance):
    set_etalon_temp(temp)
    m4i.set_sine_output(excitation_aom_channel, excitation_aom_frequency, excitation_aom_amplitude)
    m4i.start_sine_outputs()
    while True:
        if np.abs(get_etalon_temp()-temp) <= tolerance:
            time.sleep(5)
            selection=input(f"Current frequency is {wavemeter_frequency()}. Press Y to confirm or N to prepare new temp.")
            if selection == "Y" or selection == "y":
                freq = wavemeter_frequency()
                m4i.stop_sine_outputs()
                return freq
            else:
                new_temp = input(f"Enter new temperature: ")
                new_temp = float(new_temp)
                m4i.stop_sine_outputs()
                prepare_new_temp(new_temp, 0.03)
                return -1

selection = input(f"Current temp is {get_etalon_temp()}. What temp would you like to set?")
selection = float(selection)
frequency = prepare_new_temp(selection, 0.03)

normalizer_power = 1

## function

from onix.headers.RigolDS1102 import RigolDS1102

def get_data():
    curr_scope = scope.ReadScope()
    ch1_out = curr_scope[1]
    ch2_out = curr_scope[2]
    return [ch1_out, ch2_out]
def capture_sample():
    epoch_times = []
    pmt_voltages = []
    pmt_times = []

    frequency = wavemeter_frequency()
    transmission_val = get_data()[0]
    print("Freq is:", wavemeter_frequency())
    try:
        m4i.stop_sine_outputs()
    except Exception:
        pass

    dg.start_capture()

    for kk in range(repeats):
        time.sleep(0.01)
        m4i.start_sequence()
        epoch_times.append(time.time())
        m4i.wait_for_sequence_complete()
        time.sleep(time_between_repeat)

    m4i.stop_sequence()
    timeout = 1
    dg.wait_for_data_ready(timeout)
    sample_rate, digitizer_data = dg.get_data()
    pmt_voltages = digitizer_data[0]
    normalizer_voltages = digitizer_data[1]
    pmt_times = [kk / sample_rate for kk in range(len(pmt_voltages[0]))]

    try:
        m4i.start_sine_outputs()
    except Exception:
        pass
    header = {
        "excitation_aom_channel": excitation_aom_channel,
        "excitation_aom_frequency": excitation_aom_frequency,
        "excitation_aom_amplitude": excitation_aom_amplitude,
        "excitation_time": excitation_time,
        "excitation_delay": excitation_delay,
        "test_aom_channel": test_aom_channel,
        "test_aom_frequency": test_aom_frequency,
        "test_aom_amplitude": test_aom_amplitude,
        "pmt_gate_ttl_channel": pmt_gate_ttl_channel,
        "measurement_time": measurement_time,
        "repeats": repeats,
        "time_between_repeat": time_between_repeat,
        "sampling_rate": sample_rate,
        "frequency": frequency,
        "transmission": transmission_val,
        "time_bucket" : time_bucket
    }
    data = {
        "pmt_times": pmt_times,
        "pmt_voltages": pmt_voltages,
        "epoch_times": epoch_times,
    }
    name = "Fluorescence Decay"
    data_id = save_experiment_data(name, data, header)
    print(data_id)


## take data
epoch_times = []
pmt_voltages = []
pmt_times = []

frequency = wavemeter_frequency()
print("Freq is:", wavemeter_frequency())
try:
    m4i.stop_sine_outputs()
except Exception:
    pass


# dg.initiate_data_acquisition()
dg.start_capture()

for kk in range(repeats):
    time.sleep(0.01)
    m4i.start_sequence()
    epoch_times.append(time.time())
    m4i.wait_for_sequence_complete()
    time.sleep(time_between_repeat)

m4i.stop_sequence()
timeout = 1
dg.wait_for_data_ready(timeout)
sample_rate, digitizer_data = dg.get_data()
pmt_voltages = digitizer_data[0]
normalizer_voltages = digitizer_data[1]
# pmt_voltages = np.average(pmt_voltages, axis=0)
pmt_times = [kk / sample_rate for kk in range(len(pmt_voltages[0]))]

try:
    m4i.start_sine_outputs()
except Exception:
    pass


## Melting scans


scope = RigolDS1102(path='/dev/usbtmc2')
scope.write(":key:force")
scope.write(":key:lock disable")


time_bucket = 0
while True:
    if etalon_scan(60, 80, 3, time_bucket, 0.03)== "interrupt":
        break
    else:
        time_bucket+=1

## save data
header = {
    "excitation_aom_channel": excitation_aom_channel,
    "excitation_aom_frequency": excitation_aom_frequency,
    "excitation_aom_amplitude": excitation_aom_amplitude,
    "excitation_time": excitation_time,
    "excitation_delay": excitation_delay,
    "test_aom_channel": test_aom_channel,
    "test_aom_frequency": test_aom_frequency,
    "test_aom_amplitude": test_aom_amplitude,
    "pmt_gate_ttl_channel": pmt_gate_ttl_channel,
    "measurement_time": measurement_time,
    "repeats": repeats,
    "time_between_repeat": time_between_repeat,
    "sampling_rate": sample_rate,
    "frequency": frequency,
    "normalizer": normalizer_voltages

}
data = {
    "pmt_times": pmt_times,
    "pmt_voltages": pmt_voltages,
    "epoch_times": epoch_times,
}
name = "Fluorescence Decay"
data_id = save_experiment_data(name, data, header)
print(data_id)

##

import matplotlib.pyplot as plt

fig, axs = plt.subplots(2,1)

axs[0].scatter(pmt_times, np.average(pmt_voltages, axis = 0))
axs[1].scatter(pmt_times, np.average(normalizer_voltages, axis = 0))

plt.show()