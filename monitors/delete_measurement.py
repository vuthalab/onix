import os
import influxdb_client
from influxdb_client import Point
from influxdb_client.client.write_api import SYNCHRONOUS

token = os.environ.get("INFLUXDB_TOKEN")
org = "onix"
url = "http://onix-pc:8086"

bucket = "testing"

client = influxdb_client.InfluxDBClient(url=url, token=token, org=org)

api = client.write_api(write_options=SYNCHRONOUS)

# point = Point("test_measurement_2")
# point.field("state", 1)
# api.write(bucket=bucket, org="onix", record=point)
# api.write(bucket=bucket, org="onix", record=point)

delete_api = client.delete_api()

# TO DELETE MEASUREMENT
# delete_api.delete('1970-01-01T00:00:00Z', '2025-04-27T00:00:00Z', '_measurement="Laser Controller"', bucket="", org="onix")

