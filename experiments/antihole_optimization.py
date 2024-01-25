
import numpy as np
from onix.headers.awg.M4i6622 import M4i6622
from onix.headers.pcie_digitizer.pcie_digitizer import Digitizer
from onix.sequences.antihole_optimization import AntiholeOptimization
from onix.units import ureg
from onix.experiments.shared import run_save_sequences, setup_digitizer
from onix.data_tools import get_experiment_data
from onix.analysis.fitter import Fitter
from onix.analysis.helper import data_groups
from scipy.optimize import basinhopping

try:
    m4i
    print("m4i is already defined.")
except Exception:
    m4i = M4i6622()

try:
    dg
    print("dg is already defined.")
except Exception:
    dg = Digitizer()

## function to run the experiment
def run_experiment(params):
    sequence = AntiholeOptimization(  # Only change the part that changed
        ao_parameters=params["ao"],
        eos_parameters=params["eos"],
        chasm_parameters=params["chasm"],
        antihole_parameters=params["antihole"],
        detect_parameters=params["detect"],
    )

    return run_save_sequences(sequence, m4i, dg, params)


def get_default_gaussian_fitter():
    def gaussian(f, f_0, a, sigma, b, c):
        numerator = (f - f_0) ** 2
        denominator = 2 * sigma ** 2
        return a * np.exp(-numerator / denominator) + c + b * (f - f_0)

    fitter = Fitter(gaussian)
    fitter.set_absolute_sigma(False)
    fitter.set_p0({"f_0": 0, "sigma": 0.3, "c": 1.0})
    return fitter


def analyze_data(data_number):
    data, headers = get_experiment_data(data_number)
    detunings = headers["detunings"].to("MHz").magnitude
    (chasm_avg, antihole_avg, rf_avg), (monitor_chasm_avg, monitor_antihole_avg, monitor_rf_avg) = data_groups(data, headers)

    try:
        ah_fit = get_default_gaussian_fitter()
        ah_fit.set_data(detunings, antihole_avg / chasm_avg)
        ah_fit.fit()
        return ah_fit
    except Exception as e:
        return None


def is_correct_data(ah_fit):
    if ah_fit is None:
        return False
    if abs(ah_fit.results["f_0"]) > 0.5:
        return False
    if abs(ah_fit.results["sigma"]) > 0.6:
        return False
    if abs(ah_fit.results["c"] - 1) > 0.2:
        return False
    if abs(ah_fit.results["b"]) > 0.2:
        return False
    return True


def merit_function(ah_fit, antihole_time):
    height = ah_fit.results["a"]
    sigma = ah_fit.results["sigma"]
    return np.abs(sigma) * np.sqrt(antihole_time) / height ** 2  # objective to minimize


## parameters
default_params = {
    "name" : "Antihole Optimization",
    "wm_channel": 5,
    "repeats": 1,
    "ao": {
        "name": "ao_dp",
        "order": 2,
        "frequency": 75 * ureg.MHz,  # TODO: rename it to "center_frequency"
        "amplitude": 2000,
        "detect_amplitude": 450,
        "rise_delay": 1.1 * ureg.us,
        "fall_delay": 0.6 * ureg.us,
    },
    "eos": {
        "ac": {
            "name": "eo_ac",
            "amplitude": 4500,  #4500
            "offset": -300 * ureg.MHz,
        },
        "bb": {
            "name": "eo_bb",
            "amplitude": 1900,  #1900
            "offset": -300 * ureg.MHz,
        },
        "ca": {
            "name": "eo_ca",
            "amplitude": 1400,  #1400
            "offset": -300 * ureg.MHz,
        },
    },
    "field_plate": {
        "name": "field_plate",
        "use": False,
        "amplitude": 4500,
        "stark_shift": 2 * ureg.MHz,
        "padding_time": 5 * ureg.ms,
    },
    "chasm": {
        "transition": "bb",
        "scan": 3 * ureg.MHz,
        "scan_rate": 5 * ureg.MHz / ureg.s,
        "detuning": 0 * ureg.MHz,
    },
    "antihole": {
        "transitions": ["ac", "ca"],
        "amplitudes": [2000, 2000],
        "times": np.array([5, 5]) * ureg.ms,
        "total_time": 0.1 * ureg.s,
    },
    "detect": {
        "transition": "bb",
        "trigger_channel": 2,
        "detunings": np.linspace(-2, 2, 20) * ureg.MHz,
        "randomize": False,
        "on_time": 10 * ureg.us,
        "off_time": 2 * ureg.us,
        "chasm_repeats": 100,  # change the names of detection repeats
        "antihole_repeats": 100,
        "rf_repeats": 100,
    },
}

default_sequence = AntiholeOptimization(
    ao_parameters=default_params["ao"],
    eos_parameters=default_params["eos"],
    chasm_parameters=default_params["chasm"],
    antihole_parameters=default_params["antihole"],
    detect_parameters=default_params["detect"],
)
default_sequence.setup_sequence()

setup_digitizer(dg, default_params["repeats"], default_sequence)

## Optimization parameters and ranges
eos_ac_offset_range_MHz = (-302, -298)
eos_ca_offset_range_MHz = (-302, -298)

eos_ac_amplitude_range = (0.5, 2.4)
eos_ca_amplitude_range = (0.5, 2.4)

antihole_ac_piecewise_time_range = (1e-3, 20e-3)
antihole_ca_piecewise_time_range = (1e-3, 20e-3)

antihole_time_range = (40e-3, 400e-3)

bounds = [
    eos_ac_offset_range_MHz,
    eos_ca_offset_range_MHz,
    eos_ac_amplitude_range,
    eos_ca_amplitude_range,
    antihole_ac_piecewise_time_range,
    antihole_ca_piecewise_time_range,
    antihole_time_range,
]

current_values = [
    -300,
    -300,
    1500,
    1500,
    10e-3,
    10e-3,
    200e-3,
]

def values_to_parameters(values):
    params = default_params.copy()
    params["eos"]["ac"]["offset"] = values[0] * ureg.MHz
    params["eos"]["ca"]["offset"] = values[1] * ureg.MHz
    params["antihole"]["amplitudes"] = [values[2] * 1000, values[3] * 1000]
    params["antihole"]["times"] = np.array([values[4], values[5]]) * ureg.s
    params["antihole"]["total_time"] = values[6] * ureg.s
    return params


def run_and_get_merit_output(values, *args):
    params = values_to_parameters(values)
    correct_data = False
    max_repeats = 2
    repeat_index = 0
    while not correct_data and repeat_index < max_repeats:
        data_id = run_experiment(params)
        ah_fit = analyze_data(data_id)
        correct_data = is_correct_data(ah_fit)
        repeat_index += 1
    if not correct_data:
        result = 100000
    else:
        result = merit_function(ah_fit, values[-1])
    print(data_id, values, result)
    return result


## run optimization
basinhopping(
    run_and_get_merit_output,
    current_values,
    T=0.1,
    minimizer_kwargs={"bounds": bounds},
)