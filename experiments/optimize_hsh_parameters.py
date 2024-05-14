import time

import numpy as np
from onix.sequences.lf_spectroscopy import LFSpectroscopy
from onix.units import ureg
from onix.experiments.shared import (
    m4i,
    dg,
    update_parameters_from_shared,
    setup_digitizer,
    run_sequence,
    save_data,
)
from tqdm import tqdm
from scipy.optimize import basinhopping
# from onix.analysis.rf_spectroscopy import (
#     gaussian,
#     averaged_data_from_number,
#     gaussian_fits_from_data,
#     ah_parameters_from_data,
#     rf_spectroscopy_ah_ratio,
#     data_identification_to_list
# )

## parameters
default_params = {
    "name": "LF Spectroscopy",
    "sequence_repeats_per_transfer": 20,
    "data_transfer_repeats": 1,
    "chasm": {
        "transitions": ["bb"], #, "rf_both"
        "scan": 2.5 * ureg.MHz,
        "durations": 50 * ureg.us,
        "repeats": 500,
        "detunings": 0 * ureg.MHz,
        "ao_amplitude": 2000,
    },
    "antihole": {
        "transitions": ["ac", "ca", "rf_b"], #, "rf_b" (for rf assist)
        "durations": [1 * ureg.ms, 1 * ureg.ms, 2 * ureg.ms],
        "repeats": 20,
        "ao_amplitude": 800,
    },
    "detect": {
        "detunings": np.linspace(-2.5, 2.5, 10) * ureg.MHz, # np.array([-2, 0]) * ureg.MHz,
        "on_time": 5 * ureg.us,
        "off_time": 0.5 * ureg.us,
        "cycles": {
            "chasm": 0,
            "antihole": 64,
            "rf": 64,
        },
        "delay": 8 * ureg.us,
    },
    "rf": {
        "amplitude": 4000,
        "T_0": 2 * ureg.ms,
        "T_e": 1 * ureg.ms,
        "T_ch": 30 * ureg.ms,
        "center_detuning": -70 * ureg.kHz,
        "scan_range": 50 * ureg.kHz,
        "use_hsh": True,
        },
    "lf": {
        "center_frequency": 168 * ureg.kHz,
        "detuning": 0 * ureg.kHz,
        "duration": 30 * ureg.ms,
        "amplitude": 32000,
    },
}
default_params = update_parameters_from_shared(default_params)

default_sequence = get_sequence(default_params)
default_sequence.setup_sequence()
setup_digitizer(
    default_sequence.analysis_parameters["digitizer_duration"],
    default_sequence.num_of_record_cycles(),
    default_params["sequence_repeats_per_transfer"],
    ch1_range=default_params["digitizer"]["ch1_range"],
    ch2_range=default_params["digitizer"]["ch2_range"],
)

## Analysis functions
import time
import traceback
from onix.data_tools import get_experiment_data
from functools import partial
from onix.analysis.fitter import Fitter
from onix.analysis.helper import group_and_average_data
import numpy as np
from matplotlib import colormaps
import matplotlib.pyplot as plt
from scipy.integrate import quad
from scipy.special import voigt_profile
import allantools
from tqdm import tqdm
from onix.analysis.t_violation import TViolation
from uncertainties import ufloat

def gaussian(f, f_0, a, sigma, b, c):
    numerator = (f - f_0) ** 2
    denominator = 2 * sigma ** 2
    return a * np.exp(-numerator / denominator) + c + b * (f - f_0)

def get_gaussian_fit(detunings, voltages, p0=None, bounds=None):
    fitter = Fitter(gaussian)
    fitter.set_absolute_sigma(False)
    fitter.set_data(detunings, voltages)
    fitter.set_p0({"f_0": 0, "c": 1, "b": 0, "sigma": 1})
    if p0 is not None:
        fitter.set_p0(p0)
    if bounds is not None:
        for bound_var, bound in bounds.items():
            fitter.set_bounds(bound_var, bound[0], bound[1])
    fitter.fit(maxfev = 10000)
    return fitter

def averaged_data_from_number(data_number):
    data, headers = get_experiment_data(data_number)
    transmissions_avg = group_and_average_data(data["transmissions_avg"], headers["params"]["detect"]["cycles"])
    monitors_avg = group_and_average_data(data["monitors_avg"], headers["params"]["detect"]["cycles"])
    return (transmissions_avg, monitors_avg, headers)

def gaussian_fits_from_data(transmissions_avg, monitors_avg, headers, default_p0=None):
    antihole_avg = transmissions_avg["antihole"]
    rf_avg = transmissions_avg["rf"]
    if "chasm" in transmissions_avg:
        chasm_avg = transmissions_avg["chasm"]
        antihole_normalized = antihole_avg / chasm_avg
        rf_normalized = rf_avg / chasm_avg
    else:
        antihole_normalized = antihole_avg
        rf_normalized = rf_avg

    detunings = headers["detunings"].to("MHz").magnitude
    use_field_plate = headers["params"]["field_plate"]["use"]
    positive_field_plate = headers["params"]["field_plate"]["amplitude"] > 0

    p0 = {"sigma": 1, "a": -0.05}
    if default_p0 is None:
        default_p0 = {}
    p0.update(default_p0)

    if not use_field_plate:
        fits = {0: {}}
        antihole_fit = get_gaussian_fit(detunings, antihole_normalized, p0=p0)
        fits[0]["ah"] = antihole_fit

        rf_fit = get_gaussian_fit(detunings, rf_normalized, p0=p0)
        fits[0]["rf"] = rf_fit
    else:
        fits = {1: {}, -1: {}}
        for label in fits.keys():
            use_positive_stark_shift = label > 0
            if use_positive_stark_shift:
                mask = detunings > 0
            else:
                mask = detunings < 0
            p0["f_0"] = label * abs(headers["params"]["field_plate"]["stark_shift"].to("MHz").magnitude)
            antihole_fit: Fitter = get_gaussian_fit(detunings[mask], antihole_normalized[mask], p0=p0)
            fits[label]["ah"] = antihole_fit

            rf_fit: Fitter = get_gaussian_fit(detunings[mask], rf_normalized[mask], p0=p0)
            fits[label]["rf"] = rf_fit
    return fits

def ah_parameters_from_data(transmissions_avg, monitors_avg, headers):
    antihole_avg = transmissions_avg["antihole"]
    rf_avg = transmissions_avg["rf"]
    if "chasm" in transmissions_avg:
        chasm_avg = transmissions_avg["chasm"]
        antihole_normalized = antihole_avg / chasm_avg
        rf_normalized = rf_avg / chasm_avg
    else:
        antihole_normalized = antihole_avg
        rf_normalized = rf_avg

    detunings = headers["detunings"].to("MHz").magnitude
    use_field_plate = headers["params"]["field_plate"]["use"]
    positive_field_plate = headers["params"]["field_plate"]["amplitude"] > 0

    if not use_field_plate:
        off_resonant_index = np.argmax(np.abs(detunings) > 0)
        on_resonant_index = 1 - off_resonant_index
        heights = {0: {}}
        backgrounds = {0: {}}
        heights[0]["ah"] = 1 - antihole_avg[on_resonant_index] / antihole_avg[off_resonant_index]
        heights[0]["rf"] = 1 - rf_avg[on_resonant_index] / rf_avg[off_resonant_index]
        backgrounds[0]["ah"] = antihole_avg[off_resonant_index]
        backgrounds[0]["rf"] = rf_avg[off_resonant_index]
    else:
        off_resonant_index_1 = 1
        off_resonant_index_2 = 0
        # off_resonant_index_2 = 1
        on_resonant_index_1 = 3
        on_resonant_index_2 = 2

        heights = {1: {}, -1: {}}
        backgrounds = {1: {}, -1: {}}

        heights[1]["ah"] = 1 - antihole_avg[on_resonant_index_1] / antihole_avg[off_resonant_index_1]
        heights[1]["rf"] = 1 - rf_avg[on_resonant_index_1] / rf_avg[off_resonant_index_1]
        heights[-1]["ah"] = 1 - antihole_avg[on_resonant_index_2] / antihole_avg[off_resonant_index_2]
        heights[-1]["rf"] = 1 - rf_avg[on_resonant_index_2] / rf_avg[off_resonant_index_2]

        backgrounds[1]["ah"] = antihole_avg[off_resonant_index_1]
        backgrounds[1]["rf"] = rf_avg[off_resonant_index_1]
        backgrounds[-1]["ah"] = antihole_avg[off_resonant_index_2]
        backgrounds[-1]["rf"] = rf_avg[off_resonant_index_2]
    return (heights, backgrounds)

def rf_spectroscopy_ah_ratio(data_numbers, method="auto"):
    rf_heights = {}
    antihole_heights = {}
    rf_backgrounds = {}
    antihole_backgrounds = {}
    headers = []
    for data_number in data_numbers:
        transmissions_avg, monitors_avg, headers_single = averaged_data_from_number(data_number)
        if method == "auto":
            detunings_len = len(headers_single["detunings"])
            if detunings_len > 4:
                method = "fit"
            else:
                method = "ratio"
        if method == "fit":
            try:
                fits = gaussian_fits_from_data(transmissions_avg, monitors_avg, headers_single)
            except RuntimeError as e:
                print(f"Fitting error for data number #{data_number}:")
                raise e
            for label in fits:
                if label not in rf_heights:
                    rf_heights[label] = []
                    antihole_heights[label] = []
                    rf_backgrounds[label] = []
                    antihole_backgrounds[label] = []
                rf_heights[label].append(abs(fits[label]["rf"].results["a"]) / fits[label]["rf"].results["c"])
                antihole_heights[label].append(abs(fits[label]["ah"].results["a"]) / fits[label]["ah"].results["c"])
                rf_backgrounds[label].append(fits[label]["rf"].results["c"])
                antihole_backgrounds[label].append(fits[label]["ah"].results["c"])
        elif method == "ratio":
            heights, backgrounds = ah_parameters_from_data(transmissions_avg, monitors_avg, headers_single)
            # heights, backgrounds = ah_parameters_from_data1(data_number)
            for label in heights:
                if label not in rf_heights:
                    rf_heights[label] = []
                    antihole_heights[label] = []
                    rf_backgrounds[label] = []
                    antihole_backgrounds[label] = []
                rf_heights[label].append(heights[label]["rf"])
                antihole_heights[label].append(heights[label]["ah"])
                rf_backgrounds[label].append(backgrounds[label]["rf"])
                antihole_backgrounds[label].append(backgrounds[label]["ah"])
        headers.append(headers_single)
    for label in rf_heights:
        rf_heights[label] = np.array(rf_heights[label])
        antihole_heights[label] = np.array(antihole_heights[label])
        rf_backgrounds[label] = np.array(rf_backgrounds[label])
        antihole_backgrounds[label] = np.array(antihole_backgrounds[label])
    return (rf_heights, antihole_heights, rf_backgrounds, antihole_backgrounds, headers)

def data_identification_to_list(data_identification):
    if isinstance(data_identification, tuple):
        return range(data_identification[0], data_identification[1] + 1)
    elif isinstance(data_identification, int):
        return [data_identification]
    else:
        # it should be a list
        return data_identification

## run experiment, analyze data, evaluate merit function
def run_experiment(params):
    rf_frequencies = np.arange(-200, 80, 20) # scan the rf center_detunings from -140 kHz to 0 kHz (inclusive) to map out the feature
    rf_frequencies *= ureg.kHz
    for kk in range(len(rf_frequencies)):
        params["rf"]["center_detuning"] = rf_frequencies[kk]
        sequence = LFSpectroscopy(params)
        data = run_sequence(sequence, params)
        data_id = save_data(sequence, params, *data)
        if kk == 0:
            first_data_id = data_id
        elif kk == len(rf_frequencies) - 1:
            last_data_id = data_id
    return first_data_id, last_data_id

def analyze_data(first_data_id, last_data_id):
    data_list = data_identification_to_list((first_data_id, last_data_id))
    rf_heights, ah_heights, rf_bgs, ah_bgs, headers = rf_spectroscopy_ah_ratio(data_list)
    xs = [header["params"]["rf"]["center_detuning"].to("kHz").magnitude for header in headers]
    ys = rf_heights[0] / ah_heights[0]
    fitter = Fitter(gaussian)
    fitter.set_data(xs, ys)
    #fitter.set_p0
    fitter.fit()
    return xs, ys, fitter

### Check the code works
first_data_id, last_data_id = run_experiment(default_params)
xs, ys, fitter = analyze_data(first_data_id, last_data_id)
fig, ax = plt.subplots()
ax.scatter(xs, ys)
ax.plot(xs, fitter.fitted_value(xs))
plt.show()


###
def is_correct_data(fit):
    if fit is None:
        return False
    if fit.results["f_0"] > -30 or fit.results["f_0"] < -100:
        return False
    if abs(fit.results["sigma"]) > 0.6:
        return False
    # should put some reasonable bounds on background, both constant and linear
    # if abs(fit.results["c"] - 1) > 0.2:
    #     return False
    # if abs(fit.results["b"]) > 0.2:
    #     return False
    return True

def merit_function(fitter):
    return fitter.results["a"] # maximize the height of the feature, perhaps we should account for width in the merit function?

## Ranges of parameters
T_ch_range = (1e-3, 50e-3)
T_0_range = (50e-6, 5e-3)
T_e_range = (50e-6, 5e-3)


bounds = [
    T_ch_range,
    T_0_range,
    T_e_range
]

current_values = [30e-3,2e-3,1e-3]

def values_to_parameters(values):
    params = default_params.copy()
    params["rf"]["T_ch"] = values[0] * ureg.s
    params["rf"]["T_0"] = values[1] * ureg.s
    params["rf"]["T_e"] = values[2] * ureg.s
    return params


def run_and_get_merit_output(values, *args):
    params = values_to_parameters(values)
    correct_data = False
    max_repeats = 2
    repeat_index = 0
    while not correct_data and repeat_index < max_repeats:
        first_data_id, last_data_id = run_experiment(params)
        fit = analyze_data(first_data_id, last_data_id)
        correct_data = is_correct_data(fit)
        repeat_index += 1
    if not correct_data:
        result = 100000
    else:
        result = merit_function(fit)
    print(first_data_id, last_data_id, values, result)
    return result
###
basinhopping(
    run_and_get_merit_output,
    current_values,
    minimizer_kwargs={"bounds": bounds},
)