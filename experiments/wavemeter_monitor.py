import time

from onix.data_tools import save_persistent_data
from onix.headers.wavemeter.wavemeter import WM


wavemeter = WM()

def wavemeter_frequency():
    freq = wavemeter.read_frequency(5)
    if isinstance(freq, str):
        return -1
    return freq


##

def save_data():
    data = {
        "times": times,
        "frequencies": frequencies
    }
    name = "Wavemeter"
    data_id = save_persistent_data(name, data)
    print(data_id)

##

frequencies = []
times = []
measurement_period_s = 10

try:
    while True:
        frequencies.append(wavemeter_frequency())
        times.append(time.time())

        time.sleep(measurement_period_s)
except KeyboardInterrupt:
    save_data()
    pass
