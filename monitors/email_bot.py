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
One day we should make this an element bot.
Relevant Links: 
https://simple-matrix-bot-lib.readthedocs.io/en/latest/quickstart.html
https://influxdb-client.readthedocs.io/en/latest/api.html
"""

#recipients = ["alek.radak@mail.utoronto.ca", "amar.vutha@utoronto.ca", "mingyufan212@gmail.com", "bassam.nima@mail.utoronto.ca", "shravankruthick.s@gmail.com"]
recipients = ["alek.radak@mail.utoronto.ca"]

high_transmission_level = 0.3 # V; what transmission level indicates the lock is on
lock_check_time = 60 * 2 # s; the time interval over which we consider the lock state

email_password = os.environ.get("EMAIL_BOT_PASSWORD")

token = os.environ.get("INFLUXDB_TOKEN")
org = "onix"
url = "http://onix-pc:8086"
query_client = influxdb_client.InfluxDBClient(url=url, token=token, org=org)
query_api = query_client.query_api()

def send_email(subject, message):
    try:
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
        mailserver.login('onix.toronto@gmail.com', email_password) 
        mailserver.sendmail('onix.toronto@gmail.com',recipients ,msg.as_string())
        mailserver.quit()
    except:
        print(f"Couldn't send {subject} email at {datetime.datetime.now().replace(microsecond=0)}") 

def check_lock(): 
    try:
        # TODO: we save data to influx every second. When we view the data on the web browser, it averages every 5 s of data.
        # We then manually change the window period to custom, and type in 1 s. 
        # Ideally we would sample the transmission in this code every 1 s. However I can't seem to get it to work.
        # The window function seems to have a minimum of 5 s. If I try less than this, it still only samples every 5 s. 
        tables = query_api.query(
        (
            f'from(bucket:"week") |> range(start: -{lock_check_time}s) '
            '|> filter(fn: (r) => r["_measurement"] == "laser_controller")'
            '|> filter(fn: (r) => r["_field"] == "transmission")'
            '|> window(every: 1s)'
        )
        )
        values =  np.array([record["_value"] for table in tables for record in table.records])
        
        influx_last_working = datetime.datetime.now().replace(microsecond=0)
        if min(values) > high_transmission_level:
            return 1
        elif max(values) < high_transmission_level:
            return 0
        else:
            return 2
    except:
        influx_broke_time = datetime.datetime.now().replace(microsecond=0)
        
        if (influx_broke_time - influx_last_working).total_seconds() > 10 * 60: # if influx has been broken for 10 minutes, we should know
            subject = f'[Lock Alert] InfluxDB Errors at {influx_broke_time}'
            message = f'InfluxDB has not properly returned transmission data since {influx_last_working}.'
            send_email(subject, message)
        return previous_lock_state
    
previous_lock_state = check_lock()
while True:
    lock_state = check_lock()
    
    # I would want relock emails to know whether we need to go to the lab and fix something
    # if previous_lock_state == 0 and lock_state == 1:
    #     current_time = datetime.datetime.now().replace(microsecond=0)
    #     subject = f'[Lock Alert] Relock at {current_time}'
    #     message = f'Lock has been working for the last {lock_check_time / 60} minutes.'
    #     send_email(subject, message) 
    if previous_lock_state != lock_state and lock_state == 0:
        current_time = datetime.datetime.now().replace(microsecond=0)
        subject = f'[Lock Alert] Lock Broke at {current_time}'
        message = f'Lock has been broken for {lock_check_time / 60} minutes.'
        send_email(subject, message) 
    
    previous_lock_state = lock_state

    time.sleep(lock_check_time)