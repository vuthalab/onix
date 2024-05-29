import subprocess

quarto_map = {
    "intensity": '041D19D76155490C',
    "frequency": '3F2B19D76155490C',
    "digitizer": '3C3319D76151B9F0',
}

def find_quarto(name, return_all = False):
    """
    Given one of "intensity", "frequency", or "digitizer", this returns the address of the quarto as a string.
    By default returns the higher tty port, as the arduino IDE typically connects to the lower one
    If return_all = True, returns a list of strings of the two tty ports
    """
    serial_number = quarto_map[name]

    #output = subprocess.check_output("ls /sys/class/tty", shell = True)
    output = subprocess.check_output("lsusb", shell = True)
    output_str = output.decode("utf-8")
    device_list = output_str.split('\n') # list of connected tty devices to the computer

    # for each tty device, get the ID_VENDOR. If no ID_VENDOR exists, go to the next tty device. If the ID_VENDOR is qNimble, check its ID_SERIAL_SHORT
    quarto_ports = []
    for i in range(len(device_list)):
        a = subprocess.getstatusoutput(f'/bin/udevadm info --name=/dev/{device_list[i]} | grep ID_VENDOR=')
        if a[0] == 0:
            id_vendor = a[1].split("=")[1]
            if "qNimble" == id_vendor and len(quarto_ports) < 2:
                s = subprocess.getstatusoutput(f'/bin/udevadm info --name=/dev/{device_list[i]} | grep ID_SERIAL_SHORT')
                device_serial_number = s[1].split("=")[1]
                if device_serial_number == serial_number:
                    quarto_ports.append("/dev/" + device_list[i])

    if return_all == True:
        return quarto_ports
    return quarto_ports[-1]

def quarto_serial_numbers():
    """
    Returns a list of all serial numbers corresponding to Quartos on the computer.
    Useful to determine serial number of a new Quarto.
    """
    #output = subprocess.check_output("ls /sys/class/tty", shell = True)
    output = subprocess.check_output("lsusb", shell = True)
    output_str = output.decode("utf-8")
    device_list = output_str.split('\n')

    serial_nums = []
    for i in range(len(device_list)):
        a = subprocess.getstatusoutput(f'/bin/udevadm info --name=/dev/{device_list[i]} | grep ID_VENDOR=')
        if a[0] == 0:
            id_vendor = a[1].split("=")[1]
            if "qNimble" == id_vendor:
                s = subprocess.getstatusoutput(f'/bin/udevadm info --name=/dev/{device_list[i]} | grep ID_SERIAL_SHORT')
                device_serial_number = s[1].split("=")[1]
                serial_nums.append(device_serial_number)

