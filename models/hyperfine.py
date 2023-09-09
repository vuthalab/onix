from onix.units import ureg


states = {
    "7F0": {
        "a": 0,
        "b": 119.2 * ureg.MHz,  # Yano1992, Lauritzen2012
        "c": 209.25 * ureg.MHz,  # Yano1992, Lauritzen2012 209.2 MHz, we think .25 is better.
    },
    "5D0": {
        "a": 454 * ureg.MHz,  # Yano1992, Lauritzen2012
        "b": 194 * ureg.MHz,  # Yano1992, Lauritzen2012
        "c": 0,
    }
}