from onix.headers.quarto_frequency_lock import Quarto
import numpy as np
import threading
import time

q = Quarto('/dev/ttyACM0')

def check_lock(): # this should be done thorugh influxDB
    avg_transmission = np.mean(q.get_transmission_data)
    if avg_transmission > 0.1:
        return 1
    else:
        return 0

def lock_long_term():
    # will run when lock is broken for a longer term
    # should send a message in element
    lock_is_long_term_broken = True

recent_lock_history = []
i = 0

while True:
    if len(recent_lock_history) < 60:
        start_lock_state = None
    else:
        if np.mean(recent_lock_history) == 1: # if lock has been on the last 5 minutes, lock_state = 1
            start_lock_state = 1
        elif np.mean(recent_lock_history) == 0: # if lock has been off the last 5 minutes, lock_state = 0
            start_lock_state = 0
        else:
            start_lock_state = 2 # if lock has not been stable the last 5 minutes, lock state = 2

    if len(recent_lock_history) < 60:
        recent_lock_history.append(check_lock())
    else:
        recent_lock_history[i] = check_lock()

    if len(recent_lock_history) < 60:
        end_lock_state = None
    else:
        if np.mean(recent_lock_history) == 1: # if lock has been on the last 5 minutes, lock_state = 1
            end_lock_state = 1
        elif np.mean(recent_lock_history) == 0: # if lock has been off the last 5 minutes, lock_state = 0
            end_lock_state = 0
        else:
            end_lock_state = 2 # if lock has not been stable the last 5 minutes, lock state = 2


    if start_lock_state == 2 and end_lock_state == 0:
        # Lock broke
        pass
    elif start_lock_state == 2 and end_lock_state == 1:
        # lock came back
        pass

    if i < 58:
        i = i+1
    else:
        i = 0
