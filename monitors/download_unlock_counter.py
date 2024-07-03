import numpy as np
import influxdb_client
from influxdb_client.client.write_api import SYNCHRONOUS
import datetime
import os
import datetime
import calendar
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
    'from(bucket:"week") |> range(start: -50s) '
    '|> filter(fn: (r) => r["_measurement"] == "laser_controller")'
    '|> filter(fn: (r) => r["_field"] == "unlock counter")'
    '|> window(every: 5s)'
)
)
values =  np.array([record["_value"] for table in tables for record in table.records])
times = [record["_time"] for table in tables for record in table.records]
#times = [str(int(t.strftime('%s')) - 14400) for t in times] # TODO: verify this is correct. Shouldn't it be +4 hours, not minus?
np.savetxt('unlock_counter_test.csv', [(times[i], values[i]) for i in range(len(times))], delimiter=',', newline = "\n", header = f"Unlock Counter for {times[0]} to {times[-1]}", fmt='%s')
