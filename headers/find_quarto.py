import subprocess

quarto_map = {
    "intensity": '041D19D76155490C',
    "frequency": '3F2B19D76155490C',
    "digitizer": '3C3319D76151B9F0',
}

def find_quarto(name, return_both = False):
    """
    Given one of "intensity", "frequency", or "digitizer", this returns the adress of the quarto as a string.
    By default returns the higher tty port, as the arduino IDE typically connects to the lower one
    If return_both = True, returns a list of strings of the two tty ports
    """
    serial_number = quarto_map[name]

    output = subprocess.check_output("ls /sys/class/tty", shell = True)
    output_str = output.decode("utf-8")
    device_list = output_str.split('\n')
    quarto_ports = []
    for i in range(len(device_list)): # make this more precise, for quarto only
        if "ttyACM" in device_list[i] and len(quarto_ports) < 2:
            s = subprocess.getstatusoutput(f'/bin/udevadm info --name=/dev/{device_list[i]} | grep ID_SERIAL_SHORT')
            if s[1].split("=")[1] == serial_number:
                quarto_ports.append(device_list[i])
    if return_both == True:
        return quarto_ports
    return quarto_ports[-1]


# return list of ID_SERIAL_SHORT of all quartos connected to computer