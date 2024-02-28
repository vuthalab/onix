import os
import time
import influxdb_client
from influxdb_client import Point
from influxdb_client.client.write_api import SYNCHRONOUS
from onix.headers.pulse_tube import PulseTube
from onix.headers.wavemeter.wavemeter import WM
from onix.headers.ctc100 import CTC100

token = os.environ.get("INFLUXDB_TOKEN")
org = "onix"
url = "http://onix-pc:8086"
bucket="permanent"

write_client = influxdb_client.InfluxDBClient(url=url, token=token, org=org)
write_api = write_client.write_api(write_options=SYNCHRONOUS)

pt = PulseTube()
wm = WM()
c = CTC100("192.168.0.202")
channels = c.channels

while True:
    try:
        point = Point("pulse_tube")
        state = pt.is_on()
        point.field("state", state)
        for kk in pt.variables:
            point.field(kk, pt.variables[kk][1])
        write_api.write(bucket=bucket, org="onix", record=point)
    except:
        print("Pulse tube error.")

    try:
        point = Point("wavemeter")
        freq = wm.read_frequency(5)
        if isinstance(freq, str):
            freq = -1
        point.field("frequency", freq)
        write_api.write(bucket=bucket, org="onix", record=point)
    except:
        print("Wavemeter error.")

    try:
        point = Point("temperatures")
        for channel in channels:
            value = c.read(channel)
            point.field(channel, value)
        write_api.write(bucket=bucket, org="onix", record=point)
    except:
        print("CTC100 error.")

    time.sleep(300)
