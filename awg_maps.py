awg_channels = {
    0 : {
        "name" : "channel_0",
        "desc" : "not connected",
        "max_allowed_amplitude" : 32768,
    },
    1 : {
        "name" : "ao_dp",
        "desc" : "double pass aom connected to ZHL-1-2W+ (29 dB gain)",
        "max_allowed_amplitude" : 3200,
    },
    2 : {
        "name" : "eo_bb",
        "desc" : "bb transition eom (max 1 W) connected to ZHL-03-5WF+ (35 dB gain)",
        "max_allowed_amplitude" : 2300,
    },
    3 : {
        "name" : "eo_ac",
        "desc" : "ac transition eom (max 1 W) connected to ZHL-03-5WF+ (35 dB gain)",
        # AWG output at 300 MHz is attenuated by ~10 dB.
        # However, sending 1 W of 300 MHz rf to the EOM causes its total optical output to decrease over time
        # This could be heating due to the 325 MHz (625 Msps sample rate - 300 MHz?)
        # For now, we set the maximum allowed amplitude to lower to avoid power drifts,
        # though the power in the 1st order sideband will not be maximized.
        "max_allowed_amplitude" : 4500,
    },
    4 : {
        "name" : "blue_laser",
        "desc" : "blue laser aom (max 0.63 W) connected to ZHL-1A (15 dB gain)",
        "max_allowed_amplitude" : 32768,
    },
    5 : {
        "name" : "eo_ca",
        "desc" : "ca transition eom (max 1 W) connected to ZHL-1-2W+ (29 dB gain)",
        "max_allowed_amplitude" : 4500,
    },
    6 : {
        "name" : "rf_coil",
        "desc" : "rf to the coil",
        "max_allowed_amplitude" : 10000,
    },
    7 : {
        "name" : "field_plate",
        "desc" : "field plate voltage",
        "max_allowed_amplitude" : 32768,
    },
}



def get_channel_from_name(name: str) -> int:
    for channel in awg_channels:
        if awg_channels[channel]["name"] == name:
            return channel
    raise ValueError(f"Channel {name} is not defined.")

