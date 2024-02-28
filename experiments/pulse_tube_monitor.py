import os
import time
import influxdb_client

from influxdb_client import Point
from influxdb_client.client.write_api import SYNCHRONOUS
from onix.headers.pulse_tube import PulseTube

pt = PulseTube()

token = os.environ.get("INFLUXDB_TOKEN")
org = "onix"
url = "http://onix-pc:8086"

write_client = influxdb_client.InfluxDBClient(url=url, token=token, org=org)

bucket="permanent_bucket"

write_api = write_client.write_api(write_options=SYNCHRONOUS)

while True:
    point = Point("pulse_tube")
    state = pt.is_on()
    point.field("state", state)
    pt.status(silent=True)
    for kk in pt.variables:
        point.field(kk, pt.variables[kk][1])
    write_api.write(bucket=bucket, org="onix", record=point)
    time.sleep(60)
