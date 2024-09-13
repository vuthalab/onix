class DP832:
    def __init__(self, usb_port: str = "/dev/usbtmc3"):
        self.fd = open(usb_port,"w+", buffering=1)

    def _write_cmd(self, cmd: str):
        self.fd.write(cmd)

    def _read(self) -> str:
        return self.fd.readline().strip()

    def get_state(self, channel: int) -> bool:
       self._write_cmd(f":OUTP:STAT? CH{channel}\n")
       state = self._read()
       return (state == "ON")

    def set_state(self, channel: int, state: bool):
        if state:
            cmd = "ON"
        else:
            cmd = "OFF"
        self._write_cmd(f":OUTP:STAT CH{channel},{cmd}\n")

    def set_current(self, channel: int, current: float):
        self._write_cmd(f"SOUR{channel}:CURR:IMM {current:.3f}\n")

    def get_current(self, channel: int) -> float:
        self._write_cmd(f":MEAS:CURR? CH{channel}\n")
        return float(self._read())
