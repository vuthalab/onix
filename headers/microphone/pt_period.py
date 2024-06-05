from onix.analysis.microphone import Microphone
import threading

"""
leave this running in q background terminal window. From an experiment, you can run

from onix.headers.microphone.pt_period import pt_period
...
Change sequence_repeats_per_transfer and data_transfer_repeats to 1
After the line 'sequence = get_sequence(params)' you should run
params["sequence_repeats_per_transfer"] = int(np.floor(pt_period / sequence.total_duration))
sequence = get_sequence(params) 

"""

get_data_time = 1e-3
pt_period = 0.7
num_periods_fit = 10
num_periods_save = 100

mic = Microphone(num_periods_fit, num_periods_save, get_data_time)

def get_data():
  threading.Timer(get_data_time, get_data).start()
  mic.get_data()

def get_fit():
  threading.Timer(pt_period, get_fit).start()
  mic.get_fit() # every time we get a fit we need to update the ''exp. rep. rate'' param

def update_pt_period():
  threading.Timer(num_periods_save * pt_period, update_pt_period).start()
  global pt_period
  if mic.period == None:
    return
  pt_period = mic.period

get_data()
get_fit()
update_pt_period()