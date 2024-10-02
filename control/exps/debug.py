from onix.control.devices import m4i, dg, quarto_e_field
from onix.control.awg_maps import get_awg_channel_from_name, get_ttl_channel_from_name
from onix.control.exps.shared import update_parameters_from_shared
from onix.units import ureg

parameters = update_parameters_from_shared({})


def set_optical(amplitude, frequency = None):
    if frequency is None:
        frequency = parameters["ao"]["frequency_ac"]
    m4i.set_sine_output(get_awg_channel_from_name(parameters["ao"]["channel_name"]), frequency, amplitude)


def set_rf(amplitude, frequency = None):
    if frequency is None:
        frequency = parameters["rf"]["avg_center_frequency"]
    m4i.set_sine_output(get_awg_channel_from_name(parameters["rf"]["channel_name"]), frequency, amplitude)

def set_shutter(state: bool):
    m4i.set_ttl_output(get_ttl_channel_from_name(parameters["shutter"]["channel_name"]), state)
