import asyncio
from ruuvi_gateway_client import gateway
from ruuvi_gateway_client.types import ParsedDatas

from typing import Iterable, Dict, Optional
from pprint import pprint

class RuuviGateway:
    def __init__(self, ip: str, username: str, password: str, sensor_names: Dict[str, str] = None, units_dict: Dict[str, str] = None) -> None:
        self._ip = ip
        self._username = username
        self._password = password
        
        # units for the quantities to be uploaded to influxdb
        if units_dict is None:
            self.units_dict = {'humidity': 'rel %', 
            'temperature': 'C', 
            'pressure': 'hPa', 
            'acceleration': '0.001g', 
            'acceleration_x': '0.001g', 
            'acceleration_y': '0.001g', 
            'acceleration_z': '0.001g', 
            'battery': 'mV'}
        # 'movement_counter': '', 
        # 'measurement_sequence_number': ''
        
        else:
            self.units_dict = units_dict

        # names of each sensor
        if sensor_names is None:
            self.sensor_names = {'CD:6F:FE:D8:1F:DD': 'ruuvi_room', 
                                 'D0:DD:3B:BD:EB:AC': 'ruuvi_laser'}
        
        else:
            self.sensor_names = sensor_names

    def _parse_data(self, data: ParsedDatas, attr_dont_save: Iterable) -> Dict[str, Dict[str, float]]:
        # turns raw data into a format that can be directly uploaded to influxdb
        data_dict = {}
        for mac, sensor_data in data.items():
            if mac in self.sensor_names.keys():
                curr_sensor_name = self.sensor_names[mac]
            else:    
                curr_sensor_name = mac
            data_dict[curr_sensor_name] = {}
            
            for quantity in sensor_data.keys():    
                if quantity not in attr_dont_save:
                    if quantity in self.units_dict.keys():
                        key_units = f'{quantity} [{self.units_dict[quantity]}]'
                        data_dict[curr_sensor_name][key_units] = sensor_data[quantity]
                    else:
                        data_dict[curr_sensor_name][quantity] = sensor_data[quantity]
        
        return data_dict
    
    async def get_data(self, attr_dont_fetch: Iterable) -> Optional[Dict[str, Dict[str, float]]]:
        # the client fetches raw data from the gateway, and the cleaned up data is returned
        # attr_dont_fetch is a list of quantities we don't want to save to influxdb
        fetch_result = await gateway.fetch_data(self._ip, self._username, self._password)
        if fetch_result.is_ok():
            data_dict = self._parse_data(fetch_result.ok_value, attr_dont_fetch)
            return data_dict
        else:
            raise RuntimeError(f'Fetch failed: {fetch_result.err_value}')


if __name__ == '__main__':
    # Example code
    STATION_IP = "192.168.0.225"
    USERNAME = "ruuvi1"
    PASSWORD = "password123"

    ruuvi = RuuviGateway(STATION_IP, USERNAME, PASSWORD)
    dont_save = ['mac', 'tx_power', 'data_format']
    x = asyncio.run(ruuvi.get_data(dont_save))
    pprint(x)


## save instructions
"""
save data in permanent and live buckets
bucket -> ruuvi_laser/ruuvi_room -> field (temperature, pressure etc.)
call the ruuvi's ruuvi_laser, ruuvi_room
"""

## IP address, API tokens etc.
"""
Network: Ethernet
Subnet mask: 255.255.255.0
Gateway: 192.168.0.1
DHCP server: 192.168.0.1

Ruuvi Gateway’s IP address: 192.168.0.225
gateway username: ruuvi1
gateway password: password123

read-only access bearer token: nVbq+x1FG7Kkco8LoYSvNezpy/Cx2C7BX3FpnPm1hBE=
read-write access bearer token: A/O3Uw4Cf1YyZPjpuzy3afxVe6Ht922mbklVchLyblw=
"""

## Old code (doesn't work sometimes but might be useful for debugging in the future)
"""
import requests

import influxdb_client
from influxdb_client import Point
from influxdb_client.client.write_api import SYNCHRONOUS

from pprint import pprint

# Getting raw data from the gateway
headers = {
    'Authorization': 'Bearer nVbq+x1FG7Kkco8LoYSvNezpy/Cx2C7BX3FpnPm1hBE=',
}

response = requests.get('http://192.168.0.225/history?decode=true', headers=headers)

# content = response.json()['data']['tags']
content = response.json()

# Picking out the data we need to store
useful_data = ['temperature', 'humidity', 'pressure']

for sensor in content.keys():
    pass

pprint(content)

# pprint(dir(response))
"""