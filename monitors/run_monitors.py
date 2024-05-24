import os
import time
import traceback
from datetime import datetime
import influxdb_client
from influxdb_client import Point
from influxdb_client.client.write_api import SYNCHRONOUS
from onix.headers.pulse_tube import PulseTube
from onix.headers.wavemeter.wavemeter import WM
from onix.headers.ctc100 import CTC100

token = os.environ.get("INFLUXDB_TOKEN")
org = "onix"
url = "http://onix-pc:8086"
bucket_permanent = "permanent"
bucket_live = "live"

write_client = influxdb_client.InfluxDBClient(url=url, token=token, org=org)
write_api = write_client.write_api(write_options=SYNCHRONOUS)

pt = PulseTube()
wm = WM()
c = CTC100("192.168.0.202")
channels = c.channels

high_freq_time = 1
low_freq_time = 280
send_permanent = True
while True:
    time_str = datetime.now().strftime("%H:%M:%S")

    if send_permanent:
        time_start = time.time()
    try:
        point = Point("pulse_tube")
        state = pt.is_on()
        point.field("state", state)
        pt.status(silent=True)
        for kk in pt.variables:
            point.field(kk, pt.variables[kk][1])
        write_api.write(bucket=bucket_live, org="onix", record=point)
        if send_permanent:
            write_api.write(bucket=bucket_permanent, org="onix", record=point)
    except:
        print(time_str + ": Pulse tube error.")
        print(traceback.format_exc())

    try:
        point = Point("wavemeter")
        freq = wm.read_frequency(5)
        power =  wm.read_laser_power(5)
        if isinstance(freq, str):
            freq = -1
            power = -1
        point.field("frequency", freq)
        point.field("power", power)

        write_api.write(bucket=bucket_live, org="onix", record=point)
        if send_permanent:
            write_api.write(bucket=bucket_permanent, org="onix", record=point)
    except:
        print(time_str + ": Wavemeter error.")
        print(traceback.format_exc())

    try:
        point = Point("temperatures")
        for channel in channels:
            value = c.read(channel)
            point.field(channel, value)
        write_api.write(bucket=bucket_live, org="onix", record=point)
        if send_permanent:
            write_api.write(bucket=bucket_permanent, org="onix", record=point)
    except:
        print(time_str + ": CTC100 error.")
        print(traceback.format_exc())

    time_end = time.time()
    delta_time = time_end - time_start
    send_permanent = False
    if delta_time >= low_freq_time:
        send_permanent = True

    time.sleep(high_freq_time)
