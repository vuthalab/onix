import subprocess
output = subprocess.check_output("ls /sys/class/tty", shell = True)
output_str = output.decode("utf-8")
device_list = output_str.split('\n')
devices = {}
for i in range(len(device_list)):
    if "ttyACM" in device_list[i]:
        s = subprocess.getstatusoutput(f'/bin/udevadm info --name=/dev/{device_list[i]} | grep ID_PATH=')
        devices[device_list[i]] = s[1].split("usb-")[1]

quarto_map = {
    "intensity": '0:7.2.3:1.0',
    "frequency": '0:7.2.2:1.2',
    "digitizer": '0:7.2.4:1.2',
}

def find_quarto(name):
    """
    Given one of "intensity", "frequency", or "digitizer", this returns the adress of the quarto as a string
    """
    id = quarto_map[name]
    tty_address = list(devices.keys())[list(devices.values()).index(id)]
    address = "/dev/" + tty_address
    return address