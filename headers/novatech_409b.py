import numpy as np
import serial


class Novatech409B:
    """Not tested."""
    def __init__(self, address="/dev/ttyUSB0", baudrate = 19200):
        self.device = serial.Serial(address, baudrate=baudrate, timeout=0.1)
        self.disable_echo()

    def reset(self):
        self.write("R")
        print(self.device.readlines())

    def write(self, command):
        self.device.write(command.encode() + b'\n')
        print(self.device.readline())  # it always prints "ok".

    def disable_echo(self):
        self.write("E D")

    def set_frequency(self, channel, value):
        self.write(f"F{channel} {value:.2f}")

    def set_phase(self, channel, value):
        value = np.fmod(value, 2 * np.pi)
        N = int(value / (2 * np.pi) * 16384)
        self.write(f"P{channel} {N}")

    def set_amplitude(self, channel, amplitude):
        N = int(amplitude * 1023)
        self.write(f"V{channel} {N}")

    def set_single_tone_mode(self):
        self.write("M 0")
    
    def set_table_mode(self):
        """Calling this function two times will turn of the table mode."""
        self.write("M t")

    def table_step(self):
        self.write("TS")

    def read_table_values(self, channel, address):
        self.write(f"D{channel} {address}")
        return self.device.readline()  # no tested

    def _address_to_hex(self, address):
        return hex(address)[2:].zfill(4)

    def _frequency_to_hex(self, frequency):
        if frequency < 0 or frequency > 171127603.1:
            raise ValueError("Frequency must be between 0 and 171127603.1 Hz.")
        return hex(int(frequency / 0.1))[2:].zfill(8)

    def _amplitude_to_hex(self, amplitude):
        if amplitude > 1 or amplitude < 0:
            raise Exception("Amplitude must be between 0 and 1.")
        return hex(int(amplitude * 1023))[2:].zfill(4)

    def _phase_to_hex(self, phase):
        phase = np.fmod(phase, 2 * np.pi)
        return hex(int(phase / (2 * np.pi) * 16384))[2:].zfill(4)

    def load_and_run_table(self, frequencies_1, amplitudes_1, phases_1, frequencies_2 = None, amplitudes_2 = None, phases_2 = None):
        N = len(frequencies_1)
        if frequencies_2 is None:
            frequencies_2 = np.zeros(N, dtype=float)
            amplitudes_2 = np.zeros(N, dtype=float)
            phases_2 = np.zeros(N, dtype=float)
        self.set_single_tone_mode()
        for kk in range(N):
            address = self._address_to_hex(kk)
            dwell = "ff"

            freq_1 = self._frequency_to_hex(frequencies_1[kk])
            amp_1 = self._amplitude_to_hex(amplitudes_1[kk])
            phase_1 = self._phase_to_hex(phases_1[kk])
            self.write(f"t0 {address} {freq_1},{phase_1},{amp_1},{dwell}")

            freq_2 = self._frequency_to_hex(frequencies_2[kk])
            amp_2 = self._amplitude_to_hex(amplitudes_2[kk])
            phase_2 = self._phase_to_hex(phases_2[kk])
            dwell = "ff"
            self.write(f"t1 {address} {freq_2},{phase_2},{amp_2},{dwell}")

        address = self._address_to_hex(N)
        freq = self._frequency_to_hex(0)
        amp = self._amplitude_to_hex(0)
        phase = self._phase_to_hex(0)
        dwell = "00"
        self.write(f"t0 {address} {freq},{amp},{phase},{dwell}")
        self.write(f"t1 {address} {freq},{amp},{phase},{dwell}")
        self.set_table_mode()


if __name__ == "__main__":
    device = Novatech409B()
