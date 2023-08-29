from units import ureg, Q_


class AOMSettings:
    def __init__(self, awg_channel: int, center_frequency: Q_, max_amplitude: float):
        self.awg_channel = awg_channel
        self.center_frequency = center_frequency
        self.max_amplitude = max_amplitude


aoms = {
    "ac": AOMSettings(
        awg_channel=0,
        center_frequency=81.4*ureg.MHz,
        max_amplitude=2300,
    ),
    "cb": AOMSettings(
        awg_channel=1,
        center_frequency=72.5*ureg.MHz,
        max_amplitude=2800,
    ),
    "bb": AOMSettings(
        awg_channel=2,
        center_frequency=117.5*ureg.MHz,
        max_amplitude=4800,
    ),
    "pd": AOMSettings(
        awg_channel=3,
        center_frequency=80*ureg.MHz,
        max_amplitude=2800,
    ),
}
