import os
import influxdb_client
from influxdb_client import Point
from influxdb_client.client.write_api import SYNCHRONOUS
import datetime
import matplotlib.pyplot as plt

token = os.environ.get("INFLUXDB_TOKEN")
org = "onix"
url = "http://onix-pc:8086"
bucket_permanent = "permanent"
bucket_live = "live"


query_client = influxdb_client.InfluxDBClient(url=url, token=token, org=org)
query_api = query_client.query_api()



p = {"_start": datetime.timedelta(hours=-1),
     "_location": "Toronto",
     "_desc": True,
     "_floatParam": 25.1,
     "_every": datetime.timedelta(minutes=5)
     }

tables = query_api.query(
    (
        'from(bucket:"live") |> range(start: -1m) '
        '|> filter(fn: (r) => r["_measurement"] == "temperatures")'
        '|> filter(fn: (r) => r["_field"] == " 4k platform")'
    )
)

data = []
times = []

# for table in tables:
#     for record in table.records:
#         times.append(record["_time"])
#         data.append(record["_value"])

data =  [record["_value"] for table in tables for record in table.records]
times = [record["_time"] for table in tables for record in table.records]

fig, ax = plt.subplots()
ax.plot(times, data)

plt.show()