from onix.headers.wavemeter.wavemeter import WM

wavemeter = WM()

def wavemeter_frequency(channel: int):
    freq = wavemeter.read_frequency(channel)
    if isinstance(freq, str):
        return -1
    return freq
