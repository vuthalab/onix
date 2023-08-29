from onix.units import ureg


states = {
    "7F0": {
        "a": 0,
        "b": 119.2 * ureg.MHz,  # Yano1992, Lauritzen2012
        "c": 209.2 * ureg.MHz,  # Yano1992, Lauritzen2012
    },
    "5D0": {
        "a": 454 * ureg.MHz,  # Yano1992, Lauritzen2012
        "b": 194 * ureg.MHz,  # Yano1992, Lauritzen2012
        "c": 0,
    }
}