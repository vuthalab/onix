import time
import traceback
from tqdm import tqdm

from functools import partial
import numpy as np

from matplotlib import colormaps
import matplotlib.pyplot as plt
from scipy.integrate import quad
from scipy.special import voigt_profile
from uncertainties import ufloat
import allantools

from onix.analysis.t_violation import TViolation
from onix.data_tools import get_experiment_data
from onix.analysis.fitter import Fitter
from onix.analysis.helper import group_and_average_data

from typing import Union, Iterable, Tuple, Annotated, Any, Dict, List

# This file contains the functions from rf_spectroscopy.ipynb with documentation.


# %% Curvefit functions

def linear(x: Union[float, np.ndarray], a: float, b: float):
    return x * a + b


def gaussianC(f: Union[float, np.ndarray], f0: float, a: float, sigma: float, c: float) -> Union[float, np.ndarray]:
    return a * np.exp(-(f - f0) ** 2 / (2 * sigma ** 2))+c


def gaussian0(f: Union[float, np.ndarray], f0: float, a: float, sigma: float) -> Union[float, np.ndarray]:
    return a * np.exp(-(f - f0) ** 2 / (2 * sigma ** 2))


def gaussian(f: Union[float, np.ndarray], f0: float, a: float, sigma: float, b: float, c: float) -> Union[float, np.ndarray]:
    return gaussianC(f, f0, a, sigma, c) + b * (f - f0)


def two_peak_gaussian(f: Union[float, np.ndarray], f1: float, f2: float, a1: float, a2: float,
                      sigma1: float, sigma2: float, b: float, c: float) -> Union[float, np.ndarray]:
    return gaussian(f, f1, a1, sigma1) + gaussian(f, f2, a2, sigma2) + c + b * f


# never used
def four_peak_gaussian(f: Union[float, np.ndarray], f1: float, f2: float, f3: float, f4: float, a1: float, a2: float, a3: float, a4: float,
                       sigma1: float, sigma2: float, sigma3: float, sigma4: float, c: float) -> Union[float, np.ndarray]:
    return gaussian(f, f1, a1, sigma1) + gaussian(f, f2, a2, sigma2) + gaussian(f, f3, a3, sigma3) + gaussian(f, f4, a4, sigma4) + c


def get_gaussian_fit(detunings: np.ndarray, voltages: np.ndarray, p0: Iterable = None, bounds: Iterable = None) -> Fitter:
    fitter = Fitter(gaussian)
    fitter.set_absolute_sigma(False)
    fitter.set_data(detunings, voltages)
    fitter.set_p0({"f_0": 0, "c": 1, "b": 0, "sigma": 1})

    if p0 is not None:
        fitter.set_p0(p0)

    if bounds is not None:
        for bound_var, bound in bounds.items():
            fitter.set_bounds(bound_var, bound[0], bound[1])

    fitter.fit(maxfev=1000000)

    return fitter


def get_gaussianC_fit(detunings: np.ndarray, voltages: np.ndarray, p0: Iterable = None) -> Fitter:
    fitter = Fitter(gaussianC)
    fitter.set_absolute_sigma(False)
    fitter.set_data(detunings, voltages)
    if p0 is not None:
        fitter.set_p0(p0)
    fitter.fit()

    return fitter


def exp_decay(t: Union[float, np.ndarray], tau: float, a: float) -> Union[float, np.ndarray]:
    return np.exp(-t / tau) * a - a


def power_law(x: Union[float, np.ndarray], expon: float, a: float) -> Union[float, np.ndarray]:
    return x ** expon * a


# %%
span = 30e3*2*np.pi


# Not used in the code
def p_excited(t: Union[float, np.ndarray], Omega: float, delta: float, tau: float):
    """_summary_

    Args:
        t (Union[float, np.ndarray]): time
        Omega (float): _description_
        delta (float): _description_
        tau (float): _description_

    Returns:
        Union[float, np.ndarray]: _description_
    """
    Omega_gen = np.sqrt(Omega**2 + delta**2)
    offset = (Omega ** 2 / Omega_gen ** 2) / 2
    # return offset + (Omega ** 2 / Omega_gen ** 2 * np.sin(Omega_gen * t / 2) ** 2 - offset) * np.exp(-t / tau)
    return offset*(1-np.cos(Omega_gen*t)*np.exp(-t/tau))


# Not used in the code
def uniform_inhomogenous_broadening(delta: float, span: float = 30e3*2*np.pi):
    return np.heaviside(span - delta, 0.5) * np.heaviside(delta + span, 0.5) / (2 * span)


# Not used in the code
def p_excited_with_inhomogenous(t: Union[float, np.ndarray], Omega: float, tau: float, a: float = 1, c: float = 0, scale_factor: float = 1):
    def integrand(delta):
        return p_excited(t, Omega * scale_factor, delta, tau) * uniform_inhomogenous_broadening(delta)
    return a * quad(integrand, -span, span)[0] + c


# %%

# Not sure what group_and_average_data is doing
def averaged_data_from_number(data_number):
    data, headers = get_experiment_data(data_number)
    transmissions_avg = group_and_average_data(
        data["transmissions_avg"], headers["params"]["detect"]["cycles"])
    monitors_avg = group_and_average_data(
        data["monitors_avg"], headers["params"]["detect"]["cycles"])
    return (transmissions_avg, monitors_avg, headers)


def gaussian_fits_from_data(transmissions_avg: Dict[str, Iterable], monitors_avg: Dict[str, Iterable],
                            headers: Dict[str, Any], default_p0: Iterable[float] = None) -> Dict[int, Dict[str, Fitter]]:
    """Fits the antihole and rf transmission dips to Gaussians. Used as a method to extract the heights of the transmission dips.

    Args:
        transmissions_avg (Dict[str, Iterable]): optical detect transmission data
        monitors_avg (Dict[str, Iterable]): _description_
        headers (Dict[str, any]): info about the data
        default_p0 (Iterable[float], optional): Initial guesses for the Gaussian fit(s). Defaults to None.

    Returns:
        Dict[int, Dict[str, Fitter]]: A fitter object for each transmission dip in antihole and rf data.
    """
    # optical transmission avg of antihole (before rf transition)
    antihole_avg = transmissions_avg["antihole"]

    # optical transmission avg after rf transition
    rf_avg = transmissions_avg["rf"]

    if "chasm" in transmissions_avg:
        # optical transmission avg of chasm (before optical ac, ca transitions)
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

    # If a field plate isn't used, there is only one antihole (no stark splitting)
    if not use_field_plate:
        fits = {0: {}}
        antihole_fit = get_gaussian_fit(detunings, antihole_normalized, p0=p0)
        fits[0]["ah"] = antihole_fit

        rf_fit = get_gaussian_fit(detunings, rf_normalized, p0=p0)
        fits[0]["rf"] = rf_fit

    # If a field plate is used, there are 2 antiholes (labelled +- 1)
    else:
        fits = {1: {}, -1: {}}
        for label in fits.keys():
            use_positive_stark_shift = label > 0
            if use_positive_stark_shift:
                mask = detunings > 0
            else:
                mask = detunings < 0
            p0["f_0"] = label * abs(headers["params"]["field_plate"]
                                    ["stark_shift"].to("MHz").magnitude)
            antihole_fit: Fitter = get_gaussian_fit(
                detunings[mask], antihole_normalized[mask], p0=p0)
            fits[label]["ah"] = antihole_fit

            rf_fit: Fitter = get_gaussian_fit(
                detunings[mask], rf_normalized[mask], p0=p0)
            fits[label]["rf"] = rf_fit
    return fits


def ah_parameters_from_data(transmissions_avg: Dict[str, Iterable], monitors_avg: Dict[str, Iterable],
                            headers: Dict[str, Any]) -> Tuple[Dict[int, Dict[str, float]], Dict[int, Dict[str, float]]]:
    """
    Finds the height of the optical transmission dips (absorption peaks) in antihole (before rf transitions)
    and rf (after rf transitions) data

    Args:
        transmissions_avg (Dict[str, Iterable]): optical detect transmission data
        monitors_avg (Dict[str, Iterable]): _description_
        headers (Dict[str, any]): info about the data

    Returns:
        Tuple[Dict[int, Dict[str, float]], Dict[int, Dict[str, float]]]: 
        Index 0 contains the height of the optical transmission dips for antihole, rf,
        index 1 contains the transmission at an off-resonance frequency for antihole, rf.
    """

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

    """
    The quantity antihole_avg[on]/antihole_avg[off] gives a measure of the height of the Gaussian
    formed by the antihole transmission spectrum (and similarly for the rf transmission). 
    However, this method of finding the height seems to amplify the systematic error (as of May 24, 2024)
    so we don't use it.
    """
    # If no field plate, there is only one antihole and rf peak each (no Stark splitting of 7F0 b-level).
    if not use_field_plate:
        off_resonant_index = np.argmax(np.abs(detunings) > 0)
        on_resonant_index = 1 - off_resonant_index
        heights = {0: {}}
        backgrounds = {0: {}}
        heights[0]["ah"] = 1 - antihole_avg[on_resonant_index] / \
            antihole_avg[off_resonant_index]
        heights[0]["rf"] = 1 - rf_avg[on_resonant_index] / \
            rf_avg[off_resonant_index]
        backgrounds[0]["ah"] = antihole_avg[off_resonant_index]
        backgrounds[0]["rf"] = rf_avg[off_resonant_index]

    # If field plate is used, then there are 2 peaks due to Stark splitting.
    else:
        off_resonant_index_1 = 1
        off_resonant_index_2 = 0
        # off_resonant_index_2 = 1
        on_resonant_index_1 = 3
        on_resonant_index_2 = 2

        heights = {1: {}, -1: {}}
        backgrounds = {1: {}, -1: {}}

        heights[1]["ah"] = 1 - antihole_avg[on_resonant_index_1] / \
            antihole_avg[off_resonant_index_1]
        heights[1]["rf"] = 1 - rf_avg[on_resonant_index_1] / \
            rf_avg[off_resonant_index_1]
        heights[-1]["ah"] = 1 - antihole_avg[on_resonant_index_2] / \
            antihole_avg[off_resonant_index_2]
        heights[-1]["rf"] = 1 - rf_avg[on_resonant_index_2] / \
            rf_avg[off_resonant_index_2]

        backgrounds[1]["ah"] = antihole_avg[off_resonant_index_1]
        backgrounds[1]["rf"] = rf_avg[off_resonant_index_1]
        backgrounds[-1]["ah"] = antihole_avg[off_resonant_index_2]
        backgrounds[-1]["rf"] = rf_avg[off_resonant_index_2]
    return (heights, backgrounds)


def ah_parameters_from_data1(data_number: int) -> Tuple[Dict[int, Dict[str, float]], Dict[int, Dict[str, float]]]:
    """
    Same function as ah_parameters_from_data() but uses a different method. Only implemented for the case of no external electric field.

    Args:
        data_number (int): data number which is to be analyzed

    Returns:
        Tuple[Dict[int, Dict[str, float]], Dict[int, Dict[str, float]]]: 
        Index 0 contains the height of the optical transmission dips for antihole, rf,
        index 1 contains the transmission at an off-resonance frequency for antihole, rf.
    """

    data, headers = get_experiment_data(data_number)
    cycles = headers["params"]["detect"]["cycles"]

    # The commented lines are the same as onix.analysis.helper.group_and_average_data()
    """
    total_cycles = sum(cycles.values())
    remainder_to_label = {}

    for kk in range(total_cycles):
        last_index_of_label = 0
        for label in cycles:
            if cycles[label] > 0:
                last_index_of_label += cycles[label]
                if kk < last_index_of_label:
                    remainder_to_label[kk] = label
                    break
    data_averages = {}

    for label in cycles:
        if cycles[label] > 0:
            data_averages[label] = []

    for kk in range(len(data["transmissions_avg"])):
        remainder = kk % total_cycles
        data_averages[remainder_to_label[remainder]].append(
            data["transmissions_avg"][kk])
    """

    data_averages = group_and_average_data(data, cycles, average=False)
    # antihole_avg = np.average(data_averages["antihole"], axis=0)
    # rf_avg = np.average(data_averages["rf"], axis=0)
    antihole_avg = np.array(data_averages["antihole"])
    rf_avg = np.array(data_averages["rf"])

    if "chasm" in data_averages:
        chasm_avg = data_averages["chasm"]
        antihole_normalized = antihole_avg / chasm_avg
        rf_normalized = rf_avg / chasm_avg
    else:
        antihole_normalized = antihole_avg
        rf_normalized = rf_avg

    detunings = headers["detunings"].to("MHz").magnitude
    use_field_plate = headers["params"]["field_plate"]["use"]
    positive_field_plate = headers["params"]["field_plate"]["amplitude"] > 0

    # same logic as ah_parameters_from_data() but this code averages the height over all cycles
    if not use_field_plate:
        off_resonant_index = np.argmax(np.abs(detunings) > 0)
        on_resonant_index = 1 - off_resonant_index
        heights = {0: {}}
        backgrounds = {0: {}}
        heights[0]["ah"] = np.average(
            1 - antihole_avg[:, on_resonant_index] / antihole_avg[:, off_resonant_index])
        heights[0]["rf"] = np.average(
            1 - rf_avg[:, on_resonant_index] / rf_avg[:, off_resonant_index])
        backgrounds[0]["ah"] = np.average(antihole_avg[off_resonant_index])
        backgrounds[0]["rf"] = np.average(rf_avg[off_resonant_index])
        # heights[0]["ah"] = 1 - np.average(antihole_avg[on_resonant_index]) / np.average(antihole_avg[off_resonant_index])
        # heights[0]["rf"] = 1 - np.average(rf_avg[on_resonant_index]) / np.average(rf_avg[off_resonant_index])
        # backgrounds[0]["ah"] = np.average(antihole_avg[off_resonant_index])
        # backgrounds[0]["rf"] = np.average(rf_avg[off_resonant_index])
    else:
        raise NotImplementedError()
    return (heights, backgrounds)


def rf_spectroscopy_ah_ratio(data_numbers: Iterable[int], method: str = "auto") \
        -> Tuple[Dict[int, np.ndarray], Dict[int, np.ndarray], Dict[int, np.ndarray], Dict[int, np.ndarray], List[Dict[str, Any]]]:
    """The main function to extract the transmission peak heights which uses gaussian_fits_from data and ah_parameters_from_data.

    Args:
        data_numbers (Iterable[int]): _description_
        method (str, optional): _description_. Defaults to "auto".

    Raises:
        e: Fitting error for a particular data number

    Returns:
        Tuple[Dict[int, np.ndarray], Dict[int, np.ndarray], Dict[int, np.ndarray], Dict[int, np.ndarray], List[Dict[str, Any]]]:
        0. heights of rf transmission peaks
        1. heights of antihole transmission peaks
        2. rf background transmission values
        3. antihole background transmission values
        4. headers for each data number
    """
    rf_heights = {}
    antihole_heights = {}
    rf_backgrounds = {}
    antihole_backgrounds = {}
    headers = []

    for data_number in data_numbers:
        transmissions_avg, monitors_avg, headers_single = averaged_data_from_number(
            data_number)

        # choosing a method
        if method == "auto":
            if len(headers_single["detunings"]) > 4:
                method = "fit"
            else:
                method = "ratio"

        if method == "fit":
            try:
                fits = gaussian_fits_from_data(
                    transmissions_avg, monitors_avg, headers_single)
            except RuntimeError as e:
                print(f"Fitting error for data number #{data_number}:")
                raise e

            for label in fits:  # [0] or [1, -1]
                if label not in rf_heights:
                    rf_heights[label] = []
                    antihole_heights[label] = []
                    rf_backgrounds[label] = []
                    antihole_backgrounds[label] = []

                # instead of fits[0/1/-1]["rf"/"antihole"] as before,
                # the data is being stored in a different way here.
                rf_heights[label].append(
                    abs(fits[label]["rf"].results["a"]) / fits[label]["rf"].results["c"])

                antihole_heights[label].append(
                    abs(fits[label]["ah"].results["a"]) / fits[label]["ah"].results["c"])

                rf_backgrounds[label].append(fits[label]["rf"].results["c"])

                antihole_backgrounds[label].append(
                    fits[label]["ah"].results["c"])

        # using the ah_parameters_from_data function, but storing the data in the same way
        # as method = "fit"
        elif method == "ratio":
            heights, backgrounds = ah_parameters_from_data(
                transmissions_avg, monitors_avg, headers_single)
            # heights, backgrounds = ah_parameters_from_data1(data_number)

            for label in heights:  # [0] or [1, -1]
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

    # converting the lists of heights into numpy arrays
    for label in rf_heights:
        rf_heights[label] = np.array(rf_heights[label])
        antihole_heights[label] = np.array(antihole_heights[label])
        rf_backgrounds[label] = np.array(rf_backgrounds[label])
        antihole_backgrounds[label] = np.array(antihole_backgrounds[label])

    return (rf_heights, antihole_heights, rf_backgrounds, antihole_backgrounds, headers)


# Turns the argument into a list
def data_identification_to_list(data_identification: Union[Tuple, int, List]):
    if isinstance(data_identification, tuple):
        return range(data_identification[0], data_identification[1] + 1)
    elif isinstance(data_identification, int):
        return [data_identification]
    else:
        # it should be a list
        return data_identification

# %%


# Not used in rf_spectroscopy.ipynb
def get_mask(array_to_mask: Iterable, xs_mask, ys_mask, limit=1.65):
    if label == "32 MHz LPF":
        mask = ys_mask < 1.99
        mask2 = ys_mask > 1.87
    else:
        mask = ys_mask < 5
        mask2 = ys_mask > 1.85
    mask = np.bitwise_and(mask, mask2)
    xs2 = xs[mask]
    as2 = array_to_mask[mask]
    ax.scatter(xs2, as2, label=label + f", std = {np.std(as2):.2g} filtered")
    return xs2, as2


def averaging_ys(xs: Iterable[float], ys: Iterable[float], Es: Iterable[float]) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Takes x, y lists and averages the ys with unique xs filters with Es. It works equivalent to these steps:
        1. First split ys into multiple sublists, each one corresponding to a unique element of xs.
        2. Split each sublist into two, conditional on the elements of Es being positive (put into ys_avg_p) or not (put into ys_avg_n)
        3. Average each sublist of ys_avg_p and ys_avg_n and return

    Args:
        xs (Iterable[float]): list to find unique items from
        ys (Iterable[float]): list to average
        Es (Iterable[float]): filter

    Returns:
        Tuple[np.ndarray, np.ndarray, np.ndarray]
    """
    xs_unique = np.unique(xs)
    ys_to_avg_p = [[] for _ in range(len(xs_unique))]
    ys_to_avg_n = [[] for _ in range(len(xs_unique))]

    for x, y, E in zip(xs, ys, Es):
        if E > 0:
            ys_to_avg_p[np.argwhere(xs_unique == x)[0][0]].append(y)
        else:
            ys_to_avg_n[np.argwhere(xs_unique == x)[0][0]].append(y)

    ys_avg_p = []
    ys_avg_n = []

    for y_list in ys_to_avg_p:
        ys_avg_p.append(np.average(y_list))
    ys_avg_p = np.array(ys_avg_p)

    for y_list in ys_to_avg_n:
        ys_avg_n.append(np.average(y_list))
    ys_avg_n = np.array(ys_avg_n)

    return xs_unique, ys_avg_p, ys_avg_n


# %%
ttt = 1.2


def get_sigma(hs, x0=0.5):
    h1 = hs[0] - hs[3]*ttt
    h2 = hs[1] - hs[3]*ttt
    h3 = hs[2] - hs[3]*ttt
    return x0 * np.sqrt(-1/np.log(h1*h3/(h2**2)))


def get_mu(hs, x0=0.5):
    h1 = hs[0] - hs[3]*ttt
    h2 = hs[1] - hs[3]*ttt
    h3 = hs[2] - hs[3]*ttt
    return -2*x0*np.log(h1/h3)/np.log(h1*h3/(h2**2))


def get_sigma(hs, x0=0.5):
    h1 = hs[0] - hs[3]
    h2 = hs[1] - hs[3]
    h3 = hs[2] - hs[3]
    return x0 * np.sqrt(np.abs(1/np.log(np.abs(1e-18 + h1*h3/(h2**2)))))


def get_mu(hs, x0=0.5):
    h1 = hs[0] - hs[3]
    h2 = hs[1] - hs[3]
    h3 = hs[2] - hs[3]
    return -2*x0*np.log(np.abs(h1/h3))/np.log(np.abs(1e-18 + h1*h3/(h2**2)))


# %%
data_groups = {
    "pt on 10 averages": (205614, 205623),
    "pt on 20 averages": (205624, 205643),
    "pt on 30 averages": (205644, 205673),

    "pt off 10 averages": (205584, 205593),
    "pt off 20 averages": (205594, 205613),
    "pt off 30 averages": (205674, 205703),

}


# %%

# We don't use these anymore
def get_allan_dev_of(plot_variable_string):
    fig, ax = plt.subplots(figsize=(12, 6))
    for ll, (label, data_group) in enumerate(data_groups.items()):
        allans = []
        allan_errs = []
        if isinstance(data_group, (list, np.ndarray)):
            pass
        elif isinstance(data_group, (tuple)):
            data_group = range(data_group[0], data_group[1]+1)
        for kk in data_group:
            data, headers = get_experiment_data(kk)
            detunings_MHz = headers["detunings"].to("MHz").magnitude
            transmissions_avg = data["transmissions_avg"]
            fitter = Fitter(lambda x, a, b: a * x + b)

            cycle_time = ((headers["params"]["detect"]["on_time"] * 2 + headers["params"]["detect"]
                          ["off_time"] * 2.5 + headers["params"]["detect"]["delay"]).to("s").magnitude) + 4e-6
            cycles = headers["params"]["detect"]["cycles"]["antihole"]

            factor = 1
            times = np.arange(cycles*factor) * cycle_time

            ah_as = []
            ah_f0s = []
            ah_sigmas = []
            ah_cs = []

            rf_as = []
            rf_f0s = []
            rf_sigmas = []
            ah_cs = []
            for jj in range(cycles):
                ah_f0s.append(get_mu(transmissions_avg[jj]))
                ah_sigmas.append(get_sigma(transmissions_avg[jj]))
            for jj in range(cycles, cycles*2):
                rf_f0s.append(get_mu(transmissions_avg[jj]))
                rf_sigmas.append(get_sigma(transmissions_avg[jj]))

            ah_f0s = np.array(ah_f0s)
            ah_sigmas = np.array(ah_sigmas)
            rf_f0s = np.array(rf_f0s)
            rf_sigmas = np.array(rf_sigmas)

            ratios_wide = rf_sigmas / ah_sigmas
            ratios_center = rf_f0s / ah_f0s

            ah_ratios = transmissions_avg[:cycles*factor,
                                          1] / transmissions_avg[:cycles*factor, 3]
            rf_ratios = transmissions_avg[cycles*factor:cycles*factor*2,
                                          1] / transmissions_avg[cycles*factor:cycles*factor*2, 3]

            ratios = (1-rf_ratios) / (1-ah_ratios + 1e-18)
            fitter.set_data(times, ratios)
            fitter.fit()

            ratios_no_bg = ratios - \
                fitter.fitted_value(times) + fitter.results["b"]
            fitter.set_data(times, ah_ratios)
            fitter.fit()

            ah_ratios_no_bg = ah_ratios - \
                fitter.fitted_value(times) + fitter.results["b"]
            fitter.set_data(times, transmissions_avg[:cycles*factor, 0])
            fitter.fit()

            ah_on_res_no_bg = transmissions_avg[:cycles*factor,
                                                0] - fitter.fitted_value(times) + fitter.results["b"]
            fitter.set_data(times, transmissions_avg[:cycles*factor, 1])
            fitter.fit()

            ah_off_res_no_bg = transmissions_avg[:cycles*factor,
                                                 1] - fitter.fitted_value(times) + fitter.results["b"]
            fitter.set_data(times, rf_ratios)
            fitter.fit()

            rf_ratios_no_bg = rf_ratios - \
                fitter.fitted_value(times) + fitter.results["b"]

            if plot_variable_string == "height":
                plot_variable = np.copy(ratios_no_bg)
            elif plot_variable_string == "width":
                plot_variable = np.copy(ratios_wide)
            elif plot_variable_string == "center":
                plot_variable = np.copy(ratios_center)

            plot_variable /= np.average(plot_variable)

            taus = np.logspace(0, np.log10(len(plot_variable) // 3), 200)
            real_taus, allan, allan_err, _ = allantools.adev(
                plot_variable, data_type="freq", taus=taus)
            real_taus *= cycle_time
            allans.append(allan)
            allan_errs.append(allan_err)

        allan_avg = np.average(allans, axis=0)
        allan_err_avg = np.average(allan_errs, axis=0)/np.sqrt(len(data_group))
        first_integration_times.append(real_taus[0])
        allan_first.append(allan_avg[0])
        allan_first_errs.append(allan_err_avg[0])
        on_times.append(headers["params"]["detect"]
                        ["on_time"].to("us").magnitude)
        label = f" {label}, amp = {headers["params"]["detect"]["ao_amplitude"]}; reps = {headers["params"]["detect"]["cycles"]["antihole"]}; on time = {
            headers["params"]["detect"]["on_time"]}; off time = {headers["params"]["detect"]["off_time"]}; delay = {headers["params"]["detect"]["delay"]}"
        print("--")
        ax.errorbar(real_taus, allan_avg, allan_err_avg,
                    fmt="o", ls=lines[ll//10], label=label)

        ax.plot(real_taus, allan_avg[0] / np.sqrt(real_taus /
                real_taus[0]), ls="-.", color="black", alpha=0.5, lw=0.2)
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_xlabel("integration time $\\tau$ (s)")
        ax.set_ylabel("antihole "+plot_variable_string+" ratio")
    # plt.legend()
    plt.tight_layout()
    plt.grid(True, which="both", ls="-")
    plt.show()


def allan_dev_of(plot_variable):
    plot_variable /= np.average(plot_variable)

    taus = np.logspace(0, np.log10(len(plot_variable) // 3), 200)
    real_taus, allan, allan_err, _ = allantools.adev(
        plot_variable, data_type="freq", taus=taus)
    real_taus *= cycle_time
    return real_taus, allan, allan_err


def allan_plots():
    fig, axs = plt.subplots(4, 1, figsize=(14, 20))
    for ll, (label, data_group) in enumerate(data_groups.items()):
        if isinstance(data_group, (list, np.ndarray)):
            pass
        elif isinstance(data_group, (tuple)):
            data_group = range(data_group[0], data_group[1]+1)

        allan_heights = []
        allan_height_errs = []
        allan_widths = []
        allan_width_errs = []
        allan_centers = []
        allan_center_errs = []
        allan_backgrounds = []
        allan_background_errs = []

        for kk in tqdm(data_group):
            data, headers = get_experiment_data(kk)
            detunings_MHz = headers["detunings"].to("MHz").magnitude
            transmissions_avg = data["transmissions_avg"]
            fitter = Fitter(lambda x, a, b: a * x + b)

            cycle_time = ((headers["params"]["detect"]["on_time"] * 2 + headers["params"]["detect"]
                          ["off_time"] * 2.5 + headers["params"]["detect"]["delay"]).to("s").magnitude) + 4e-6
            cycles = headers["params"]["detect"]["cycles"]["antihole"]

            factor = 1
            times = np.arange(cycles*factor) * cycle_time

            ah_as = []
            ah_f0s = []
            ah_sigmas = []
            ah_cs = []

            rf_as = []
            rf_f0s = []
            rf_sigmas = []
            rf_cs = []

            # print(kk)
            for jj in range(cycles):
                antihole_fit = get_gaussian_fit(
                    detunings_MHz, transmissions_avg[jj])
                ah_as.append(antihole_fit.results["a"])
                ah_f0s.append(antihole_fit.results["f_0"])
                ah_sigmas.append(antihole_fit.results["sigma"])
                ah_cs.append(antihole_fit.results["c"])

            for jj in range(cycles, cycles*2):
                antihole_fit = get_gaussian_fit(
                    detunings_MHz, transmissions_avg[jj])
                rf_as.append(rf_fit.results["a"])
                rf_f0s.append(rf_fit.results["f_0"])
                rf_sigmas.append(rf_fit.results["sigma"])
                rf_cs.append(rf_fit.results["c"])

            ah_as = np.array(ah_as)
            ah_f0s = np.array(ah_f0s)
            ah_sigmas = np.array(ah_sigmas)
            ah_cs = np.array(ah_cs)

            rf_as = np.array(rf_as)
            rf_f0s = np.array(rf_f0s)
            rf_sigmas = np.array(rf_sigmas)
            rf_cs = np.array(rf_cs)

            ratios_height = rf_as / ah_as
            ratios_width = rf_sigmas / ah_sigmas
            ratios_center = rf_f0s / ah_f0s
            ratios_background = rf_cs / ah_cs

            taus = np.logspace(0, np.log10(len(ratios_height) // 3), 200)
            real_taus, allan_height, allan_height_err, _ = allantools.adev(
                ratios_height / np.average(ratios_height), data_type="freq", taus=taus)
            _, allan_width, allan_width_err, _ = allantools.adev(
                ratios_width / np.average(ratios_width), data_type="freq", taus=taus)
            _, allan_center, allan_center_err, _ = allantools.adev(
                ratios_center / np.average(ratios_center), data_type="freq", taus=taus)
            _, allan_background, allan_background_err, _ = allantools.adev(
                ratios_background / np.average(ratios_background), data_type="freq", taus=taus)
            real_taus *= cycle_time

            allan_heights.append(allan_height)
            allan_height_errs.append(allan_height_err)
            allan_widths.append(allan_width)
            allan_width_errs.append(allan_width_err)
            allan_centers.append(allan_center)
            allan_center_errs.append(allan_center_err)
            allan_backgrounds.append(allan_background)
            allan_background_errs.append(allan_background_err)

        # first_integration_times.append(real_taus[0])
        # on_times.append(headers["params"]["detect"]["on_time"].to("us").magnitude)
        # label = f"{label}, amp = {headers["params"]["detect"]["ao_amplitude"]}; reps = {headers["params"]["detect"]["cycles"]["antihole"]}; on time = {headers["params"]["detect"]["on_time"]}; off time = {headers["params"]["detect"]["off_time"]}; delay = {headers["params"]["detect"]["delay"]}"

        allan_height_avg = np.average(allan_heights, axis=0)
        allan_height_err_avg = np.average(
            allan_height_errs, axis=0)/np.sqrt(len(data_group))
        axs[0].errorbar(real_taus, allan_height_avg, allan_height_err_avg,
                        fmt="o", ls=lines[ll//10], label=label)
        axs[0].plot(real_taus, allan_height_avg[0] / np.sqrt(real_taus /
                    real_taus[0]), ls="-.", color="black", alpha=0.5, lw=0.2)
        axs[0].set_xscale("log")
        axs[0].set_yscale("log")
        axs[0].set_xlabel("integration time $\\tau$ (s)")
        axs[0].set_ylabel("antihole height ratio")
        axs[0].grid(True, which="both", ls="-")

        allan_width_avg = np.average(allan_widths, axis=0)
        allan_width_err_avg = np.average(
            allan_width_errs, axis=0)/np.sqrt(len(data_group))
        axs[1].errorbar(real_taus, allan_width_avg, allan_width_err_avg,
                        fmt="o", ls=lines[ll//10], label=label)
        axs[1].plot(real_taus, allan_width_avg[0] / np.sqrt(real_taus /
                    real_taus[0]), ls="-.", color="black", alpha=0.5, lw=0.2)
        axs[1].set_xscale("log")
        axs[1].set_yscale("log")
        axs[1].set_xlabel("integration time $\\tau$ (s)")
        axs[1].set_ylabel("antihole width ratio")
        axs[1].grid(True, which="both", ls="-")

        allan_center_avg = np.average(allan_centers, axis=0)
        allan_center_err_avg = np.average(
            allan_center_errs, axis=0)/np.sqrt(len(data_group))
        axs[2].errorbar(real_taus, allan_center_avg, allan_center_err_avg,
                        fmt="o", ls=lines[ll//10], label=label)
        axs[2].plot(real_taus, allan_center_avg[0] / np.sqrt(real_taus /
                    real_taus[0]), ls="-.", color="black", alpha=0.5, lw=0.2)
        axs[2].set_xscale("log")
        axs[2].set_yscale("log")
        axs[2].set_xlabel("integration time $\\tau$ (s)")
        axs[2].set_ylabel("antihole center ratio")
        axs[2].grid(True, which="both", ls="-")

        allan_background_avg = np.average(allan_backgrounds, axis=0)
        allan_background_err_avg = np.average(
            allan_background_errs, axis=0)/np.sqrt(len(data_group))
        axs[3].errorbar(real_taus, allan_background_avg,
                        allan_background_err_avg, fmt="o", ls=lines[ll//10], label=label)
        axs[3].plot(real_taus, allan_background_avg[0] / np.sqrt(real_taus /
                    real_taus[0]), ls="-.", color="black", alpha=0.5, lw=0.2)
        axs[3].set_xscale("log")
        axs[3].set_yscale("log")
        axs[3].set_xlabel("integration time $\\tau$ (s)")
        axs[3].set_ylabel("antihole constant background ratio")
        axs[3].grid(True, which="both", ls="-")

    axs[0].legend(bbox_to_anchor=(0, 1.02, 1, 0.2),
                  loc="lower left", mode="expand", ncol=1)
    plt.tight_layout()
    plt.grid(True, which="both", ls="-")
    plt.show()
