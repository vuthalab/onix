import os
import time
import traceback
import asyncio
from datetime import datetime

import influxdb_client
from influxdb_client import Point
from influxdb_client.client.write_api import SYNCHRONOUS

from onix.headers.pulse_tube import PulseTube
from onix.headers.wavemeter.wavemeter import WM
from onix.headers.ctc100 import CTC100
from onix.headers.ruuvi_gateway import RuuviGateway
from onix.headers.frg730 import FRG730

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

ruuvi_g = RuuviGateway(ip='192.168.0.225', username='ruuvi1', password='password123')
ruuvi_dont_save = ['mac', 'tx_power', 'data_format']

pressure_gauge = FRG730()

high_freq_time = 1
low_freq_time = 280
send_permanent = True
print("Connected to all devices.")
ctc_error = []

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
        ctc_error.clear()
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
        ctc_error.append(0)
        if len(ctc_error) >= 10:
            try: 
                c.close()
            except:
                pass
            try:
                c = CTC100("192.168.0.202")
            except:
                print(time_str + ": Couldn't reconnect to CTC100.")

    try:    # uploading data from temperature sensors
        ruuvi_data_dict = asyncio.run(ruuvi_g.get_data(ruuvi_dont_save))

        # data is stored in dicts as {sensor_name: {quantity: value}}
        for sensor_name in ruuvi_data_dict.keys():
            point = Point(sensor_name)

            for quantity, value in ruuvi_data_dict[sensor_name].items():
                point.field(quantity, value)

            write_api.write(bucket=bucket_live, org="onix", record=point)
            if send_permanent:
                write_api.write(bucket=bucket_permanent, org="onix", record=point)
    except:
        print(time_str + ": Ruuvi gateway error.")
        print(traceback.format_exc())
    
    try:
        point = Point("pressure_gauge")

        pressure_unknown_units = pressure_gauge.pressure.nominal_value
        if pressure_gauge.units == 'torr':
            point.field("pressure (torr)", pressure_unknown_units)

        elif pressure_gauge.units == 'mbar':
            point.field('pressure (torr)', pressure_unknown_units*0.750062)    # 1mbar = 0.750062 torr

        elif pressure_gauge.units == 'Pa':
            point.field('pressure (torr)', pressure_unknown_units*0.00750062) # 1 Pa = 0.00750062 torr

        write_api.write(bucket=bucket_live, org="onix", record=point)
        if send_permanent:
            write_api.write(bucket=bucket_permanent, org="onix", record=point)
    except:
        print(time_str + ": Pressure gauge error.")
        print(traceback.format_exc())

    time_end = time.time()
    delta_time = time_end - time_start
    send_permanent = False
    if delta_time >= low_freq_time:
        send_permanent = True

    time.sleep(high_freq_time)
