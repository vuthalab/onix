import numpy as np
import time
import influxdb_client
from influxdb_client.client.write_api import SYNCHRONOUS
import datetime
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import datetime


"""
Query cavity transmission from influxDB every 5 seconds. Write 1 to recent_lock_history if the lock is on. Write 0 if lock is off.
Do this in a rolling manner, so that the list always contains the 60 most recent numbers (i.e. the list considers the lock behavior for past five minutes).
Take the mean of recent_lock_history to determine the state of the lock over the last 5 minutes. 
If the lock goes from locked to unlocked, i.e. mean from 1/60 to 0, the bot should send a message.
If the lock goes from unlocked to locked, i.e. mean from 59/60 to 1, the bot should send a message.

One day we should make this an element bot.
Relevant Links: 
https://simple-matrix-bot-lib.readthedocs.io/en/latest/quickstart.html
https://influxdb-client.readthedocs.io/en/latest/api.html
"""

recipients = ["alek.radak@mail.utoronto.ca", "amar.vutha@utoronto.ca", "mingyufan212@gmail.com", "bassam.nima@mail.utoronto.ca"]

high_transmission_level = 0.3 # V; what transmission level indicates the lock is on
instantaneous_lock_delta_t = 5 # check the lock every 5 seconds
long_term_lock_delta_t = 60 * 5 # long term behavior of the lock is determined by its lock state over the last 5 minutes
N = long_term_lock_delta_t // instantaneous_lock_delta_t


def send_email(lockstate):
    time = datetime.datetime.now().replace(microsecond=0)
    if lockstate == "broke":
        subject = f"[Lock Alert] Lock Broke at {time}"
        message = f"Lock Broke at {time}"
    elif lockstate == "relock":
        subject = f"[Lock Alert] Relock at {time}"
        message = f"Relock at {time}"
    elif lockstate == "unstable":
        subject = f"[Lock Alert] Unstable at {time}"
        message = f"Unstable at {time}"
    elif lockstate == "code error":
        subject = f"[Lock Alert] Code broke at {time}"
        message = f"Code broke at {time}"
    elif lockstate == "code fixed":
        subject = f"[Lock Alert] Code fixed at {time}"
        message = f"Code is no longer broken at {time}"

    msg = MIMEMultipart()
    msg['From'] = 'onix.toronto@gmail.com'
    msg['To'] = 'onix.toronto@gmail.com'
    msg['Subject'] = subject
    message = message
    msg.attach(MIMEText(message))
    mailserver = smtplib.SMTP('smtp.gmail.com',587)
    mailserver.ehlo()
    mailserver.starttls()
    mailserver.ehlo()
    mailserver.login('onix.toronto@gmail.com', 'pmnk chkz ptdx rnlv')
    mailserver.sendmail('onix.toronto@gmail.com',recipients ,msg.as_string())
    mailserver.quit()
    print(f'Email {lockstate} sent.')

def check_instantaneous_lock(): 
    """
    Query indluxdb for the most recent transmission point. First argument is 1 if high and 0 is low.
    Second argument is 0 if we got the data from influx without issue. This returns 1 if there was some error.
    """
    try:
        token = os.environ.get("INFLUXDB_TOKEN")
        org = "onix"
        url = "http://onix-pc:8086"

        query_client = influxdb_client.InfluxDBClient(url=url, token=token, org=org)
        query_api = query_client.query_api()

        tables = query_api.query(
        (
            'from(bucket:"week") |> range(start: -20s) '
            '|> filter(fn: (r) => r["_measurement"] == "laser_controller")'
            '|> filter(fn: (r) => r["_field"] == "transmission")'
        )
        )
        values =  np.array([record["_value"] for table in tables for record in table.records])
    
        transmission =  values[-1]
    except: # if there is some error in getting the transmission then return the average value, but keep track of errors
        return np.mean(recent_lock_history), 1
    
    if transmission > high_transmission_level:
        return 1, 0
    else:
        return 0, 0

def check_long_term_lock():
    if np.mean(recent_lock_history) == 1: # if lock has been on the last 5 minutes, lock_state = 1
        return 1
    elif np.mean(recent_lock_history) == 0: # if lock has been off the last 5 minutes, lock_state = 0
        return 0
    else:
       return 2 # if lock has not been stable the last 5 minutes, lock state = 2
    
def check_error_state():
    if np.mean(errors_list) == 1: # code is fully broken over the last five minutes
        return 1
    elif np.mean(errors_list) == 0: # code is fully working over the last five minutes
        return 0
    else:
        return 2 # code has been unstable over last five minutes

errors_list = []
recent_lock_history = []
i = 0

while True:
    if len(recent_lock_history) < N:
        start_lock_state = None
        start_error_state = None
    else:
        start_lock_state = check_long_term_lock()
        start_error_state = check_error_state()
       
    state, error = check_instantaneous_lock()
    if len(recent_lock_history) < N:
        recent_lock_history.append(state)
        errors_list.append(error)
    else:
        recent_lock_history[i] = state
        errors_list[i] = error

    if len(recent_lock_history) < N:
        end_lock_state = None
        end_error_state = None
    else:
       end_lock_state = check_long_term_lock()
       end_error_state = check_error_state()

    if start_lock_state != None and end_lock_state != None:
        if start_lock_state != end_lock_state and end_lock_state == 0:
            send_email("broke") 
        elif start_lock_state != end_lock_state and end_lock_state == 1:
            send_email("relock")
        elif start_lock_state != end_lock_state and end_lock_state == 2:
            send_email("unstable")
    if start_error_state != None and end_error_state != None:
        if start_error_state != end_error_state and end_error_state == 1:
            send_email("code error") 
        elif start_error_state != end_error_state and end_error_state == 0:
            send_email("code fixed")

    if i < N-1:
        i = i+1
    else:
        i = 0
    
    time.sleep(instantaneous_lock_delta_t)
