from ruuvitag_sensor.ruuvi import RuuviTagSensor


def handle_data(found_data):
    print(f"MAC {found_data[0]}")
    print(f"Data {found_data[1]}")


if __name__ == "__main__":
    RuuviTagSensor.get_data(handle_data)