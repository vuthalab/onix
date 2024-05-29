import subprocess

output = subprocess.check_output("ls /sys/class/tty", shell = True)
output_str = output.decode("utf-8")
device_list = output_str.split('\n')
devices = {}
for i in range(len(device_list)):
    if "ttyACM" in device_list[i]:
        s = subprocess.getstatusoutput(f'/bin/udevadm info --name=/dev/{device_list[i]} | grep ID_SERIAL_SHORT')
        devices[device_list[i]] = s[1].split("=")[1]

quarto_map = {
    "intensity": '041D19D76155490C',
    "frequency": '3F2B19D76155490C',
    "digitizer": '3C3319D76151B9F0',
}

def find_quarto(name):
    """
    Given one of "intensity", "frequency", or "digitizer", this returns the adress of the quarto as a string
    """
    id = quarto_map[name]
    all_ttys = [key for key in devices if devices[key] == id] # returns a list ["ttyACMX", "ttyACMY"] of the two ports connected to this quarto
    tty_address = devices[all_ttys[-1]]
    address = "/dev/" + tty_address
    return address