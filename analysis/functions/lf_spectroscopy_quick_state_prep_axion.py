import numpy as np
import matplotlib.pyplot as plt
from uncertainties import unumpy
from onix.data_tools import get_experiment_data
from onix.analysis.fitter import Fitter
from onix.analysis.functions.shared import get_normalized_transmission, data_identification_to_list

"""
Functions for the LFQuickStatePrepAxion sequence / experiment. 
"""

def gaussian_fit(f, f0, a, sigma, c):
    return np.exp(-(f-f0)**2 / sigma**2) * a + c

def double_gaussian_fit_linear_term(f, f1, f2, a1, a2, sigma, m, b):
    return gaussian_fit(f, f1, a1, sigma, 0) + gaussian_fit(f, f2, a2, sigma, 0) + m*f + b

def double_gaussian_fit(f, f1, f2, a1, a2, sigma, b):
    return gaussian_fit(f, f1, a1, sigma, 0) + gaussian_fit(f, f2, a2, sigma, 0) + b
    
def get_double_gaussian_fitter(fs, pops, errs = None, linear_term = False, p0: dict = None, fitted_freq_offset = np.inf, fitted_amp_difference = np.inf, chi_cutoff = np.inf):
    """
    Fits optical holes to the sum of two Gaussians. Can add a linear term to account for slope.
    Has a default initial guess which can be updated using p0 argument. Works best if stark splitting is input as initial guess.

    Fit is determined to be bad if any of the following occur:
    - fitted center frequencies are outside of fitted_freq_offset MHz from the initial guess
    - fitted amplitudes are more than a factor of fitted_amp_difference different
    - chi^2 > chi_cutoff

    If the fit is bad, or cannot fit at all, return None. 
    """
    guess = {
            "f1": -np.average(np.abs(fs)),
            "f2": np.average(np.abs(fs)),
            "a1": np.max(pops) - np.min(pops),
            "a2": np.max(pops) - np.min(pops),
            "sigma": np.average(np.abs(fs)) / 4,
            "b": np.min(pops),
        }

    if linear_term:
        fitter = Fitter(double_gaussian_fit_linear_term)
        guess["m"] = (pops[-1] - pops[0]) / (fs[-1] - fs[0])
    else:
        fitter = Fitter(double_gaussian_fit)

    if errs is None:    
        fitter.set_data(fs, pops)
    else:
        fitter.set_data(fs, pops, errs)
        
    fitter.set_bounds("a1", 0, np.inf)
    fitter.set_bounds("a2", 0, np.inf)
    fitter.set_bounds("sigma", 0, np.inf)
    
    if p0 is not None:
        for i in p0:
            guess[i] = p0[i]
            
    fitter.set_p0(guess)
  
    try: 
        fitter.fit()
        freq1_diff = np.abs(fitter.results["f1"] - guess["f1"])
        freq2_diff = np.abs(fitter.results["f2"] - guess["f2"])
        amplitude_diff = fitter.results["a1"] / fitter.results["a2"]
        if errs is None:
            # if no errs we have no chi^2 to consider
            if (freq1_diff < fitted_freq_offset) and (freq2_diff < fitted_freq_offset) and (amplitude_diff < fitted_amp_difference) and (amplitude_diff > 1/fitted_amp_difference):
                return fitter
            else:
                return None
        else:
            # with errs ensure that chi^2 is below cutoff
            if (freq1_diff < fitted_freq_offset) and (freq2_diff < fitted_freq_offset) and (amplitude_diff < fitted_amp_difference) and (amplitude_diff > 1/fitted_amp_difference) and (fitter.reduced_chi < chi_cutoff):
                return fitter
            else:
                return None
    except:
        return None

def get_experiment_result(data_number):
    detunings, data, header = get_normalized_transmission(data_number)
    total_pop_1 = 1
    if "1" in data:
        pop_other_state_1 = data["1"] - data["2"]
    else:
        pop_other_state_1 = - data["2"]
    return (header, detunings, pop_other_state_1, total_pop_1)

def get_results(data_identification, fitted_freq_offset = np.inf, fitted_amp_difference = np.inf, chi_cutoff = np.inf):
    """
    Input the data identification for one Ramsey fringe. Fits the optical holes. 

    """
    data_list = data_identification_to_list(data_identification)
    headers = []
    results = []
    for data_number in data_list:
        header, detunings, pop_other_state, total_pop = get_experiment_result(data_number)
        stark_shift = header["params"]["field_plate"]["stark_shift"].magnitude
        if len(detunings) > 2:
            # change here to add filtering of bad hole fits
            fitter = get_double_gaussian_fitter(
                detunings,
                unumpy.nominal_values(pop_other_state),
                p0 = {"f1":-stark_shift, "f2": stark_shift},
                fitted_freq_offset = fitted_freq_offset,
                fitted_amp_difference = fitted_amp_difference,
                chi_cutoff = chi_cutoff
                )
            if fitter is None:
                return None, None
            else:
                headers.append(header)
                results.append(
                    unumpy.uarray(
                        [fitter.results["a1"], fitter.results["a2"]],
                        [fitter.errors["a1"], fitter.errors["a2"]],
                    )
                )
        else:
            headers.append(header)
            results.append(pop_other_state)
    return headers, np.array(results)

def plot_hole(data_number, linear_term = False, errorbars = True, plot = True, note = None, fitted_freq_offset = np.inf, fitted_amp_difference = np.inf, chi_cutoff = np.inf):
    """
    Plots the optical holes for one experiment. 
    - Can add a linear term
    - Can add a note to the the plot where you might list some parameters of the experiment
    - Allows for you to specify what makes a bad fit. 
    """
    header, detunings, pop_other_state, total_pop = get_experiment_result(data_number)
    vals = unumpy.nominal_values(pop_other_state)
    errs = unumpy.std_devs(pop_other_state)
    
    if not errorbars:
        errs = None

    d, h = get_experiment_data(data_number)
    stark_shift = h["params"]["field_plate"]["stark_shift"].magnitude
    

    fitter = get_double_gaussian_fitter(
        detunings, 
        vals, 
        errs, 
        linear_term = linear_term, 
        p0 = {"f1": - stark_shift, "f2": stark_shift}, 
        fitted_freq_offset = fitted_freq_offset, 
        fitted_amp_difference = fitted_amp_difference, 
        chi_cutoff = chi_cutoff
        )
 
    
    if plot: 
        fig, ax = plt.subplots()
        f_axis = np.linspace(np.min(detunings), np.max(detunings), 1000)
        
        if errorbars:
            ax.errorbar(detunings, vals, errs, fmt="o", ls="")
            if fitter is not None:
                ax.text(0.8,1.02, fitter.all_results_str(), transform = ax.transAxes)
        else:
            ax.scatter(detunings, vals)
            if fitter is not None:
                ax.text(0.8,1.02, "\n".join(fitter.all_results_str().split('\n')[:-1]), transform = ax.transAxes)
        
        
        if fitter is not None:
            ax.plot(f_axis, fitter.fitted_value(f_axis), alpha = 0.5)
        else:
            ax.text(0.1,0.9, "Bad fit", transform = ax.transAxes)

        ax.text(0, 1.02, "#" + str(data_number), transform = ax.transAxes)

        if note is not None:
            ax.text(0.1,0.1, note, transform = ax.transAxes)

        ax.set_xlabel("optical detuning (MHz)")
        ax.set_ylabel("absorption")
        ax.grid()
        plt.tight_layout()
        plt.show()

    return fitter

def plot_hole_multi(data_number, linear_term = False, errorbars = True, plot = True, note = None, fitted_freq_offset = np.inf, fitted_amp_difference = np.inf, chi_cutoff = np.inf):
    """
    Plots all holes for one Ramsey fringe worth of experiments starting from data_number
    """
    header = get_experiment_result(data_number)[0]
    counter = 0
    while counter < len(header["params"]["lf"]["phase_diffs"]):
        plot_hole(
            data_number+counter, 
            linear_term = linear_term, 
            errorbars = errorbars, 
            plot = plot, 
            note = note,
            fitted_freq_offset = fitted_freq_offset,
            fitted_amp_difference = fitted_amp_difference,
            chi_cutoff = chi_cutoff
            )
            
        counter+=1

def histogram_slopes(data_range, max, bins = 30, plot = True, title = None):
    """
    Fit the holes of these data sets to the sum of two Gaussians with linear background and background offset.
    Histogram the results with E > 0 and E < 0 in different colors.
    """

    slopes_E_pos = []
    slopes_E_neg = []

    start_num = data_range[0]
    package_size = data_range[1] - data_range[0] + 1
    
    e_start_pos = False
    d, h = get_experiment_data(start_num)
    if h["params"]["field_plate"]["amplitude"] > 0:
        e_start_pos = True
    
    while start_num <= max:
        for kk in range(package_size):
            fitter = plot_hole(start_num+kk, linear_term = True, plot = False)
            if e_start_pos is True:
                slopes_E_pos.append(fitter.results["m"])
            else:
                slopes_E_neg.append(fitter.results["m"])

        for kk in range(package_size):
            fitter = plot_hole(start_num+kk, linear_term = True, plot = False)
            if e_start_pos is True:
                slopes_E_neg.append(fitter.results["m"])
            else:
                slopes_E_pos.append(fitter.results["m"])
    
        start_num += 2*package_size
    
    figures = 2 # number of significant digits to print mean and standard deviation

    slopes_str = f"Mean E>0 = {np.mean(slopes_E_pos):.{figures}g} \t STDEV E>0 = {np.std(slopes_E_pos):.{figures}g} \n Mean E<0 = {np.mean(slopes_E_neg):.{figures}g} \t STDEV E<0 = {np.std(slopes_E_neg):.{figures}g}"
    if plot:
        fig, ax = plt.subplots()
        ax.hist(slopes_E_pos, bins = bins, label = "$E>0$", alpha = 0.5)
        ax.hist(slopes_E_neg, bins = bins, label = "$E<0$", alpha = 0.5)
        ax.text(0, 1.02, f"#{data_range[0]} - #{max}", transform = ax.transAxes)
        ax.text(0.1,0.03, slopes_str, transform = ax.transAxes)
        ax.set_xlabel("Fitted slope (arb)")
        ax.set_ylabel("Counts")
        ax.legend()
        ax.grid()
        if title is not None:
            ax.set_title(title)
    print(slopes_str)
    return slopes_E_pos, slopes_E_neg