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
Code to download the unlock counter to a csv
"""

token = os.environ.get("INFLUXDB_TOKEN")
org = "onix"
url = "http://onix-pc:8086"

query_client = influxdb_client.InfluxDBClient(url=url, token=token, org=org)
query_api = query_client.query_api()

tables = query_api.query(
(
    'from(bucket:"week") |> range(start: -7d) '
    '|> filter(fn: (r) => r["_measurement"] == "laser_controller")'
    '|> filter(fn: (r) => r["_field"] == "unlock counter")'
    '|> window(every: 5s)'
)
)
values =  np.array([record["_value"] for table in tables for record in table.records])
times = [record["_time"] for table in tables for record in table.records]
np.savetxt('unlock_counter.csv', [(times[i], values[i]) for i in range(len(times))], delimiter=',', newline = "\n", header = "Unlock Counter for June 25, 2024 to July 2, 2024", fmt='%s')
