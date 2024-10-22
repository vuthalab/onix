import os
import datetime

import influxdb_client
import numpy as np


class InfluxDBQuery:
    def __init__(self):
        token = os.environ.get("INFLUXDB_TOKEN")
        org = "onix"
        url = "http://onix-pc:8086"
        client = influxdb_client.InfluxDBClient(url=url, token=token, org=org)
        self._api = client.query_api()
        now = datetime.datetime.now()
        local_now = now.astimezone()
        self._local_tz = local_now.tzinfo

    def list_measurements(self, bucket):
        """Lists all measurements under a bucket."""
        query = f'import "influxdata/influxdb/schema"\n\nschema.measurements(bucket: "{bucket}")'
        measurements = []
        tables = self._api.query(query)
        for table in tables:
            for record in table:
                measurements.append(record["_value"])
        return measurements

    def list_fields(self, bucket, measurement, start="-30d", stop="now()"):
        """Lists all fields under a measurement between the start and stop times."""
        query = (
            'import "influxdata/influxdb/schema"'
            '\nschema.measurementFieldKeys('
            f'bucket: "{bucket}", '
            f'measurement: "{measurement}", '
            f'start: {start}, '
            f'stop: {stop}, '
            ')'
        )
        fields = []
        tables = self._api.query(query)
        for table in tables:
            for record in table:
                fields.append(record["_value"])
        return fields

    def get_field_last_value(self, bucket, measurement, field):
        query = (
            f'from(bucket:"{bucket}")'
            f'|> range(start: 0)'
            f'|> filter(fn: (r) => r["_measurement"] == "{measurement}")'
            f'|> filter(fn: (r) => r["_field"] == "{field}")'
            '|> last()'
        )
        tables = self._api.query(query)
        data = [record["_value"] for table in tables for record in table.records]
        times = [record["_time"].astimezone(self._local_tz) for table in tables for record in table.records]
        return (times[0], data[0])
    
    def get_field_values(self, bucket, measurement, field, start="-1h", stop="now()", average_time=None):
        """Get the values of a field."""
        query = (
            f'from(bucket:"{bucket}")'
            f'|> range(start: {start}, stop: {stop})'
            f'|> filter(fn: (r) => r["_measurement"] == "{measurement}")'
            f'|> filter(fn: (r) => r["_field"] == "{field}")'
        )
        if average_time is not None:
            query += f'|> aggregateWindow(every: {average_time}, fn: mean, createEmpty: false)'
        tables = self._api.query(query)
        data = [record["_value"] for table in tables for record in table.records]
        times = [record["_time"].astimezone(self._local_tz) for table in tables for record in table.records]
        return (np.array(times), np.array(data))

