import numpy as np
import time
import influxdb_client
from influxdb_client import Point
from influxdb_client.client.write_api import SYNCHRONOUS
import datetime

"""
A side project for anyone if they have time. Query cavity transmission from influxDB every 5 seconds. Write 1 to recent_lock_history if the lock is on. Write 0 if lock is off.
Do this in a rolling manner, so that the list always contains the 60 most recent numbers (i.e. the list considers the lock behavior for past five minutes).
Take the mean of recent_lock_history to determine the state of the lock over the last 5 minutes. 
If the lock goes from locked to unlocked, i.e. mean from 1/60 to 0, the element bot should send a message.
If the lock goes from unlocked to locked, i.e. mean from 59/60 to 1, the element bot should send a message.

Set up the element bot to message in a new channel. Call the channel something liek ''ONIX bot''. 


Relevant Links: 
https://simple-matrix-bot-lib.readthedocs.io/en/latest/quickstart.html
https://influxdb-client.readthedocs.io/en/latest/api.html
"""

high_transmission_level = 0.1 # V; what transmission level indicates the lock is on
instantaneous_lock_delta_t = 5 # check the lock every 5 seconds
long_term_lock_delta_t = 60 * 5 # long term behavior of the lock is determined by its lock state over the last 5 minutes
N = long_term_lock_delta_t // instantaneous_lock_delta_t

def check_instantaneous_lock(): # should get the most recent influxDB point and return 1 if transmission is high, zero otherwise
    query_client = influxdb_client
    token = "" # get token
    org = "onix"
    url = "http://onix-pc:8086"

    query_client = influxdb_client.InfluxDBClient(url=url, token=token, org=org)
    query_api = query_client.query_api()
    # p = {"_start": datetime.timedelta(hours=-24),
    #     "_location": "Toronto",
    #     "_desc": True,
    #     "_floatParam": 25.1,
    #     "_every": datetime.timedelta(seconds=0.1)
    #     }
    tables = query_api.query(
    (
        'from(bucket:"week") |> range(start: -5s) '
        '|> filter(fn: (r) => r["_measurement"] == "laser_controller")'
        '|> filter(fn: (r) => r["_field"] == "transmission")'
    )
    )
    values =  np.array([record["_value"] for table in tables for record in table.records])
    transmission =  values[-1]
    if transmission > high_transmission_level:
        return 1
    else:
        return 0

def check_long_term_lock():
    if np.mean(recent_lock_history) == 1: # if lock has been on the last 5 minutes, lock_state = 1
        return 1
    elif np.mean(recent_lock_history) == 0: # if lock has been off the last 5 minutes, lock_state = 0
        return 0
    else:
       return 2 # if lock has not been stable the last 5 minutes, lock state = 2

recent_lock_history = []
i = 0

while True:
    if len(recent_lock_history) < N:
        start_lock_state = None
    else:
        start_lock_state = check_long_term_lock()
       
    if len(recent_lock_history) < N:
        recent_lock_history.append(check_instantaneous_lock())
    else:
        recent_lock_history[i] = check_instantaneous_lock()

    if len(recent_lock_history) < N:
        end_lock_state = None
    else:
       end_lock_state = check_long_term_lock()

    if start_lock_state != None and end_lock_state != None:
        if start_lock_state != end_lock_state and end_lock_state == 0:
            # Lock broke
            pass
        elif start_lock_state != end_lock_state and end_lock_state == 1:
            # lock came back
            pass

    if i < N-1:
        i = i+1
    else:
        i = 0
    
    time.sleep(5)