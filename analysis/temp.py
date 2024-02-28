import influxdb_client, os, time
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
from onix.headers.ctc100 import CTC100

c = CTC100("192.168.0.202")
channels = c.channels

# token = os.environ.get("INFLUXDB_TOKEN")
token = "eEFnkmmH4l8_Md_-3wstSl467udnMjFyO3oR-seY84UZaYVJU2ZejkxIHN0YdzVQ1LMAs7vlT_jMXbYJ_2H0pw=="
org = "onix"
url = "http://localhost:8086"

write_client = influxdb_client.InfluxDBClient(url=url, token=token, org=org)

bucket="never_deleted"

write_api = write_client.write_api(write_options=SYNCHRONOUS)
   
# for value in range(5):
#   point = (
#     Point("measurement1")
#     .tag("tagname1", "tagvalue1")
#     .field("field1", value)
#   )
#   write_api.write(bucket=bucket, org="onix", record=point)
#   time.sleep(1) # separate points by 1 second

while(True):
    for channel in channels:
        value = c.read(channel)
        point = (
            Point("temperatures2")
            # .tag(channel, "tagvalue1")
            .field(channel, value)
        )
        write_api.write(bucket=bucket, org="onix", record=point)
    print("t")
    print(time.time())
    time.sleep(2)