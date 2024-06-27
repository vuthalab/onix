import numpy as np
import time
import influxdb_client
from influxdb_client import Point
from influxdb_client.client.write_api import SYNCHRONOUS
import datetime
import os

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

high_transmission_level = 0.3 # V; what transmission level indicates the lock is on
instantaneous_lock_delta_t = 5 # check the lock every 5 seconds
long_term_lock_delta_t = 60 * 5 # long term behavior of the lock is determined by its lock state over the last 5 minutes
N = long_term_lock_delta_t // instantaneous_lock_delta_t

def check_instantaneous_lock(): # should get the most recent influxDB point and return 1 if transmission is high, zero otherwise
    
    token = os.environ.get("INFLUXDB_TOKEN")
    org = "onix"
    url = "http://onix-pc:8086"

    query_client = influxdb_client.InfluxDBClient(url=url, token=token, org=org)
    query_api = query_client.query_api()

    

    query_client = influxdb_client.InfluxDBClient(url=url, token=token, org=org)
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


check_instantaneous_lock()

# import os
# os.environ.get("INFLUXDB_TOKEN")