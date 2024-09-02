import os

import matplotlib.pyplot as plt
import numpy as np
import onix.models.hyperfine as hyperfine
import pandas
from onix.analysis.fitter import Fitter
from onix.analysis.functions.shared import (analysis_dnum,
                                            data_identification_to_list)
from onix.data_tools import get_analysis_file_path
from uncertainties import ufloat, unumpy

"""
Shared analysis functions for any LF Ramsey spectroscopy. 
"""

def averaging_ys(xs, ys):
    """
    Given multiple traces with the same phases this averages all traces into one. 
    """
    xs_unique = np.unique(xs)
    ys_to_avg = [[] for _ in range(len(xs_unique))]
    for x, y in zip(xs, ys):
        ys_to_avg[np.argwhere(xs_unique == x)[0][0]].append(y)
    ys_avg = []
    ys_std = []
    for y_list in ys_to_avg:
        ys_avg.append(np.average(y_list))
        ys_std.append(np.std(y_list))
    ys_avg = np.array(ys_avg)
    ys_std = np.array(ys_std)
    
    return xs_unique, ys_avg, ys_std

def phase_fit(phi, A, C, phi_0):
    return A * np.cos(phi - phi_0) + C

def get_phase_fitter(phases, heights, height_errs):
    """
    Given Ramsey data (phases, heights, and errors) this fits to a A cos(phi - phi_0) + C and returns the fitter.
    """
    fitter = Fitter(phase_fit)
    fitter.set_data(phases, heights, height_errs)
    fitter.set_bounds("A", 0, np.inf)

    # setting this bound makes weird fits for certain phi_0's because they want to fit to a value outside the bound
    # fitter.set_bounds("phi_0", 0, 2*np.pi)
    fitter.fit()
    return fitter

def plot_ramsey(data, get_results, do_average = True):
    """
    Plot Ramsey fringes given the data dictionary. 
    get_results will be specific to the detections we use (i.e. detect_1 - detect_2 vs detect_3 - detect_6)
    get_results will be defined in the file specific functions file, so just pass get_results = get_results
    """
    index = []
    fig, ax = plt.subplots(figsize = (10, 6), dpi = 120)
    for ll, (label, data_range) in enumerate(data.items()):
        headers, results_temp = get_results(data_range)
        mask = np.ones(len(headers), dtype=bool)
        for kk, header in enumerate(headers):
            sequence = header["params"]["sequence"]["sequence"]
            for name, repeat in sequence:
                if name.startswith("lf") and not name.endswith("piov2"):
                    index.append(int(name.split("_")[-1]))
                    break
        xs = np.array([header["params"]["lf"]["phase_diffs"][index[kk]] for kk, header in enumerate(headers)])
        if results_temp.ndim == 1:
            ys = unumpy.nominal_values(results_temp)[1:]
            errs = unumpy.std_devs(results_temp)[1:]
            ax.errorbar(xs, ys, errs, label=label, marker='o', linestyle='')
        else:
            for kk in range(0, 2):
                ys = unumpy.nominal_values(results_temp[:, kk])
                errs = unumpy.std_devs(results_temp[:, kk])
                if do_average:
                    xs_avg, ys_avg, errs_avg = averaging_ys(xs[mask], ys[mask])
                else:
                    xs_avg, ys_avg, errs_avg = xs, ys, errs
                if kk == 0:
                    lambda_label = ", $\\lambda = +1$"
                else:
                    lambda_label = ", $\\lambda = -1$"
                ax.scatter(xs_avg, ys_avg, label=label + lambda_label, marker='o', linestyle='')
                fitter = get_phase_fitter(xs_avg, ys_avg, None)
                xs_fit = np.linspace(np.min(xs_avg), np.max(xs_avg), 100)
                ys_fit = fitter.fitted_value(xs_fit)
                ax.plot(xs_fit, ys_fit)
                if kk == 0:
                    label_str = label + " $\\lambda = +1$ \n" + fitter.all_results_str()
                    ax.text(0,1.02, label_str, transform = ax.transAxes)
                else:
                    label_str = label + " $\\lambda = -1$ \n" + fitter.all_results_str()
                    ax.text(0.3,1.02, label_str, transform = ax.transAxes)
                print(fitter.result_str("A"))
                print(fitter.result_str("C"))
                print(fitter.result_str("phi_0"))

    ax.set_xlabel("Ramsey phase difference")
    ax.set_ylabel("absorption - offset (arb. unit)")
    ax.text(0.8,1.02,f"#{data_range[0]} - #{data_range[1]}" , transform = ax.transAxes)
    ax.text(0.6,1.02, f"SNR = {round(fitter.results['A']/fitter.errors['A'],2)}", transform = ax.transAxes)
    ax.legend()
    ax.grid()
    plt.tight_layout()
    #plt.show()
    print(f"SNR with 9 phase points = {fitter.results['A']/fitter.errors['A']}")
    return fig, ax

#############################################################################################################
magnetic_field = 223e-4 # measured magnetic field, see https://electricatoms.wordpress.com/2024/06/26/improving-the-onix-magnetic-field-version-1/

# compute nuclear spins for conversion from b, bbar or a, abar frequencies to W_T
ground = hyperfine.states["7F0"]
ground._Hamiltonian = ground.H_total(magnetic_field)
e_g, s_g = ground.energies_and_eigenstates()

a_I_dot_n = ground.m_Ix(s_g[0])
abar_I_dot_n = ground.m_Ix(s_g[1])
b_I_dot_n = ground.m_Ix(s_g[2])
bbar_I_dot_n = ground.m_Ix(s_g[3])
I_a = (abar_I_dot_n - a_I_dot_n) / 2
I_b = (bbar_I_dot_n - b_I_dot_n) / 2

def combine_polarization_data(results):
    def check_equal_and_append(check_from, check_name, append_to):
        check_col = check_from[:, col_indices[check_name]]
        count = np.unique(check_col)
        if len(count) > 1:
            raise Exception(f"{check_name} is not the same.")
        append_to.append(check_col[0])

    results_array = pandas.DataFrame.from_dict(results).to_numpy()
    keys = list(results.keys())
    indices = list(range(len(keys)))
    col_indices = dict(zip(keys, indices))
    data = {
        "f+": [],
        "f-": [],
        "start_time": [],
        "end_time": [],
        "temp": [],
        "phi0+": [],
        "phi0-": [],
    }
    group_size = 2
    for kk in range(len(results_array) // group_size):
        sub_data = results_array[kk * group_size: kk * group_size + group_size]
        data_indices = []
        for name in results.keys():
            if name not in ["start_time", "end_time", "D", "freq_center", "temp", "phi0"]:
                if name not in data:
                    data[name] = []
                check_equal_and_append(sub_data, name, data[name])
        for ll, datapoint in enumerate(sub_data):
            if ll == 0:
                start_time = datapoint[col_indices["start_time"]]
            if ll == len(sub_data) - 1:
                end_time = datapoint[col_indices["end_time"]]
            if datapoint[col_indices["D"]]:
                f_p = datapoint[col_indices["freq_center"]]
                phi0_p = datapoint[col_indices["phi0"]]
            else:
                f_m = datapoint[col_indices["freq_center"]]
                phi0_m = datapoint[col_indices["phi0"]]


        data["f+"].append(f_p)
        data["f-"].append(f_m)
        data["phi0+"].append(phi0_p)
        data["phi0-"].append(phi0_m)
        data["start_time"].append(start_time)
        data["end_time"].append(end_time)
        data["temp"].append(np.nanmean(sub_data[:, col_indices["temp"]]))

    data["f+"] = np.array(data["f+"])
    data["f-"] = np.array(data["f-"])
    data["phi0+"] = np.array(data["phi0+"])
    data["phi0-"] = np.array(data["phi0-"])
    data["Z"] = (data["f+"] + data["f-"]) / 4
    data["W_T"] = []
    for kk in range(len(data["f+"])):
        if data["state"][kk] == "a":
            I = I_a
        else:
            I = I_b
        data["W_T"].append((data["f+"][kk] - data["f-"][kk]) / 4 / I)

    keys = list(data.keys())
    indices = list(range(len(keys)))
    col_indices = dict(zip(keys, indices))
    data = pandas.DataFrame.from_dict(data).to_numpy()
    return data, col_indices

def analyze_data(data_range, max, get_results, ignore_data_numbers = [], load_old = True, save_new = True):
    """
    Analyzes a collection of Ramsey phase scans. get_results depends on the specific sequence, so input get_results = get_results
    load_old determines if this will search for the processed data and load it
    save_new determines if this will save the processed data
    """
    points_per_scan = data_range[1] - data_range[0] + 1 

    first = data_range[0]
    num_completed_scans = np.floor((max + 1 - data_range[0]) / points_per_scan)
    last = int(num_completed_scans * points_per_scan + data_range[0] - 1) # ignore the unfinished last Ramsey fringe, if any
    
    first_unprocessed = first
    all_old_data = False
    all_new_data = True
    loaded_data = None

    path_to_save = get_analysis_file_path(analysis_dnum, f"{first}_{last}_processed.npz") # filepath we will end up saving our data to
    directory_to_save = os.path.dirname(path_to_save) # directory where all of our processed data is saved
    if load_old is True: # if load old data, search the processed data folder for filenames matching these data numbers
        for file in os.listdir(directory_to_save):
            try: # Sometimes we save data with longer filenames that just first_last_processed. These will cause errors in the below line.
                start_str, stop_str, _ = file.split("_")
            except:
                continue 
            start = int(start_str)
            stop = int(stop_str)
            if start == data_range[0]: # if two datasets have the same start number, they ought to be the same
                all_new_data = False
                if stop >= last: # recognizing that all data you are trying to load has already been analyzed
                    all_old_data = True
                    if stop > last:
                        print("You are attempting to analyze a subset of an already analyzed dataset. This has returned the larger dataset, not just the data numbers you asked for. Retry with load_old = False, save_new = False.")
                first_unprocessed = stop + 1 # setting the datapoint where we should start our analysis
                old_data_path = os.path.join(directory_to_save, file) # load old data
                loaded_data = np.load(old_data_path, allow_pickle = True)
                print("Existing data loaded")
                break
        
    current = first_unprocessed + points_per_scan - 1 # end of the first unprocessed Ramsey fringe
    offset = 0 # we will add points_per_scan to this as we analyze each Ramsey fringe
    # temporary housing for all of the quanitities we will save from each Ramsey fringe 
    all_results = {
        "lf_center_freq": [],
        "freq_center": [],
        "state": [],
        "E": [],
        "D": [],
        "field_plate_amplitude": [],
        "electric_field_shift_MHz": [],
        "pulse_time_ms": [],
        "wait_time_ms": [],
        "ramp_time_ms": [],
        "start_time": [],
        "end_time": [],
        "temp": [],
        "rf_amplitude": [],
        "rf_duration_ms": [],
        "phi0": [],
    }

    # if we have new data to analyze, analyze it
    if all_old_data is False:
        while current + offset <= last:
            # data range corresponding to the next Ramsey fringe which needs to be analyzed
            data_range_now = (first_unprocessed + offset, first_unprocessed + offset + points_per_scan - 1)

            # if this data range intersects ignore_data_numbers, keep adding 1 to this data range until we are out of ignore_data_numbers
            if data_range_now[0] in ignore_data_numbers:
                offset += 1
                continue

            # convert our data range into a list
            data_list = data_identification_to_list(data_range_now)

            try: 
                # gets the headers and the fitted heights to our antiholes. Can filter out bad fits, although likely not necessary.
                headers, results = get_results(
                    data_range_now, 
                    fitted_freq_offset = np.inf,
                    fitted_amp_difference = np.inf,
                    chi_cutoff = np.inf
                )
                if headers is None:
                    offset += len(list(data_list))
                    continue
            except Exception as e:
                offset += len(list(data_list))
                print(e)
                continue
        
            # if temperature could not be saved for this experiment, set it to nan
            for header in headers:
                if "temp" not in header or header["temp"] is None:
                    header["temp"] = np.nan
        
            # this list will store the index of the phase points, for example [0,1,2,3] if we use 4 phase points, or 0-7 if we use 8
            index = []
            for header in headers:
                sequence = header["params"]["sequence"]["sequence"]
                for name, repeat in sequence:
                    if name.startswith("lf") and not name.endswith("piov2"):
                        index.append(int(name.split("_")[-1]))
                        break

            # get the relevant experiment parameters for this Ramsey fringe            
            center_freq = headers[0]["params"]["lf"]["center_frequency"].to("Hz").magnitude
            pulse_time_ms = headers[0]["params"]["lf"]["piov2_time"].to("ms").magnitude
            wait_time_ms = headers[0]["params"]["lf"]["wait_time"].to("ms").magnitude
            total_time_ms = pulse_time_ms + wait_time_ms
            detuning = headers[0]["params"]["lf"]["detuning"].to("Hz").magnitude
            ramp_time = headers[0]["params"]["field_plate"]["ramp_time"].to("ms").magnitude
            probe_freq = center_freq + detuning
            fp_amplitude = headers[0]["params"]["field_plate"]["amplitude"]
            stark_shift = headers[0]["params"]["field_plate"]["stark_shift"].to("MHz").magnitude
            detect_detuning = headers[0]["params"]["detect"]["detunings"].to("MHz").magnitude
            E_field = fp_amplitude > 0
            phases = [header["params"]["lf"]["phase_diffs"][index[kk]] for kk, header in enumerate(headers)]
            temp = np.nanmean([header["temp"] for header in headers])
            rf_amplitude = headers[0]["params"]["rf"]["amplitude"]
            rf_duration_ms = headers[0]["params"]["rf"]["HSH"]["T_ch"].to("ms").magnitude
        
            for kk in range(2):  # positive and negative Stark components.
                ys = unumpy.nominal_values(results[:, kk])
                errs = unumpy.std_devs(results[:, kk])
                try:
                    fitter = get_phase_fitter(phases, ys, None)
                except Exception as e:
                    print(f"Could not fit Ramsey fringe for data numbers #{first_unprocessed + offset} - #{first_unprocessed + offset + points_per_scan - 1}. \n Fix this and try the analysis again. \n Perhaps add these to ignore_data_numbers?")
                    return "Fix the Ramsey fringe which could not be fit and try again.", 0
                # move the fitted phi_0 to be between +- pi
                phi0 = ufloat(fitter.results["phi_0"], fitter.errors["phi_0"])
                phi0 = (np.pi + phi0) % (2 * np.pi) - np.pi
                freq_center = phi0 / (2 * np.pi) / (total_time_ms * 1e-3) + probe_freq # convert phi_0 to center frequency of transition
                
                # append all relevant data to all_results dictionary
                neg_DdotE = kk == 0
                E = E_field
                D = (not neg_DdotE) == E
                epoch_times = (
                    headers[0]["data_info"]["save_epoch_time"],
                    headers[-1]["data_info"]["save_epoch_time"],
                )
                if probe_freq > 200e3:
                    state = "a"
                else:
                    state = "b"
                all_results["lf_center_freq"].append(center_freq)
                all_results["freq_center"].append(freq_center)
                all_results["state"].append(state)
                all_results["E"].append(E)
                all_results["D"].append(D)
                all_results["start_time"].append(epoch_times[0])
                all_results["end_time"].append(epoch_times[1])
                all_results["pulse_time_ms"].append(pulse_time_ms)
                all_results["wait_time_ms"].append(wait_time_ms)
                all_results["field_plate_amplitude"].append(fp_amplitude)
                all_results["electric_field_shift_MHz"].append(stark_shift)
                all_results["ramp_time_ms"].append(ramp_time)
                all_results["temp"].append(temp)
                all_results["rf_amplitude"].append(rf_amplitude)
                all_results["rf_duration_ms"].append(rf_duration_ms)
                all_results["phi0"].append(phi0)
            
            # increment the offset to move to the next Ramsey fringe
            offset += len(list(data_list))
        
        # format our all_results dictionary, containing all newly-analyzed data, into a numpy array
        new_results, col_indices = combine_polarization_data(all_results)

        # if there is no old data we loaded, return new_results
        if loaded_data is None:
            results = new_results
        # concatenate loaded data and new data
        else:
            
            if "results" in loaded_data:
                results = np.concatenate((loaded_data["results"], new_results), axis = 0)
            else:
                # put the loaded data back into a nice array
                f_plus_nominal = loaded_data["f_plus_nominal"]
                f_plus_uncertainty = loaded_data["f_plus_uncertainty"]
                f_minus_nominal = loaded_data["f_minus_nominal"]
                f_minus_uncertainty = loaded_data["f_minus_uncertainty"]
                phi_plus_nominal = loaded_data["phi_plus_nominal"]
                phi_plus_uncertainty = loaded_data["phi_plus_uncertainty"]
                phi_minus_nominal = loaded_data["phi_minus_nominal"]
                phi_minus_uncertainty = loaded_data["phi_minus_uncertainty"]
                Z_nominal = loaded_data["Z_nominal"]
                Z_uncertainty = loaded_data["Z_uncertainty"]
                W_T_nominal = loaded_data["W_T_nominal"]
                W_T_uncertainty = loaded_data["W_T_uncertainty"]
                start_time = loaded_data["start_time"]
                end_time = loaded_data["end_time"]
                temp = loaded_data["temp"]
                lf_center_freq  = loaded_data["lf_center_freq"]
                state = loaded_data["state"]
                E = loaded_data["E"]
                field_plate_amplitude = loaded_data["field_plate_amplitude"]
                electric_field_shift_MHz = loaded_data["electric_field_shift_MHz"]
                pulse_time_ms = loaded_data["pulse_time_ms"]
                wait_time_ms = loaded_data["wait_time_ms"]
                ramp_time_ms = loaded_data["ramp_time_ms"]
                rf_amplitude = loaded_data["rf_amplitude"]
                rf_duration_ms = loaded_data["rf_duration_ms"]
                # TODO: the ordering is hard coded here. This should instead reference col_indices to always get the ordering right even if something changes.
                loaded_data_results = np.array([
                    np.array([
                        ufloat(f_plus_nominal[i], f_plus_uncertainty[i]),
                        ufloat(f_minus_nominal[i], f_minus_uncertainty[i]),
                        start_time[i],
                        end_time[i],
                        temp[i],
                        ufloat(phi_plus_nominal[i], phi_plus_uncertainty[i]),
                        ufloat(phi_minus_nominal[i], phi_minus_uncertainty[i]),
                        lf_center_freq[i],
                        state[i],
                        E[i],
                        field_plate_amplitude[i],
                        electric_field_shift_MHz[i],
                        pulse_time_ms[i],
                        wait_time_ms[i],
                        ramp_time_ms[i],
                        rf_amplitude[i],
                        rf_duration_ms[i],
                        ufloat(Z_nominal[i], Z_uncertainty[i]),
                        ufloat(W_T_nominal[i], W_T_uncertainty[i])
                        ]) for i in range(len(f_plus_nominal))
                    ])
                results = np.concatenate((loaded_data_results, new_results), axis = 0)

        # TODO: automate this. If there is any column which has unumpy values, create two lists, one with the nominal values and one with the uncertainties

        f_plus_nominal = [unumpy.nominal_values(i).tolist() for i in results[:, col_indices["f+"]]]
        f_plus_uncertainty = [unumpy.std_devs(i).tolist() for i in results[:, col_indices["f+"]]]

        f_minus_nominal = [unumpy.nominal_values(i).tolist() for i in results[:, col_indices["f-"]]]
        f_minus_uncertainty = [unumpy.std_devs(i).tolist() for i in results[:, col_indices["f-"]]]

        phi_plus_nominal = [unumpy.nominal_values(i).tolist() for i in results[:, col_indices["phi0+"]]]
        phi_plus_uncertainty = [unumpy.std_devs(i).tolist() for i in results[:, col_indices["phi0+"]]]

        phi_minus_nominal = [unumpy.nominal_values(i).tolist() for i in results[:, col_indices["phi0-"]]]
        phi_minus_uncertainty = [unumpy.std_devs(i).tolist() for i in results[:, col_indices["phi0-"]]]

        Z_nominal = [unumpy.nominal_values(i).tolist() for i in results[:, col_indices["Z"]]]
        Z_uncertainty = [unumpy.std_devs(i).tolist() for i in results[:, col_indices["Z"]]]

        W_T_nominal = [unumpy.nominal_values(i).tolist() for i in results[:, col_indices["W_T"]]]
        W_T_uncertainty = [unumpy.std_devs(i).tolist() for i in results[:, col_indices["W_T"]]]


        # try to save the new data. If it saves without error, then delete the old file.
        if save_new:
            try:
                #np.savez(path_to_save, results=results, col_indices=col_indices)
                np.savez(path_to_save, 
                         f_plus_nominal = f_plus_nominal, 
                         f_plus_uncertainty = f_plus_uncertainty, 
                         f_minus_nominal = f_minus_nominal, 
                         f_minus_uncertainty = f_minus_uncertainty, 
                         phi_plus_nominal = phi_plus_nominal, 
                         phi_plus_uncertainty = phi_plus_uncertainty, 
                         phi_minus_nominal = phi_minus_nominal, 
                         phi_minus_uncertainty = phi_minus_uncertainty,
                         Z_nominal = Z_nominal, 
                         Z_uncertainty = Z_uncertainty,
                         W_T_nominal = W_T_nominal, 
                         W_T_uncertainty = W_T_uncertainty,
                         start_time = results[:, col_indices["start_time"]],
                         end_time = results[:, col_indices["end_time"]],
                         temp = results[:, col_indices["temp"]],
                         lf_center_freq  = results[:, col_indices["lf_center_freq"]],
                         state = results[:, col_indices["state"]],
                         E = results[:, col_indices["E"]],
                         field_plate_amplitude = results[:, col_indices["field_plate_amplitude"]],
                         electric_field_shift_MHz = results[:, col_indices["electric_field_shift_MHz"]],
                         pulse_time_ms = results[:, col_indices["pulse_time_ms"]],
                         wait_time_ms = results[:, col_indices["wait_time_ms"]],
                         ramp_time_ms = results[:, col_indices["ramp_time_ms"]],
                         rf_amplitude = results[:, col_indices["rf_amplitude"]],
                         rf_duration_ms = results[:, col_indices["rf_duration_ms"]],
                         )
                if all_new_data is False:
                    os.remove(old_data_path)
            except Exception as e:
                print(f"Could not save new data with exception {e}")
                return results, col_indices

    # if there is no new data, just return the previously loaded data
    else:
        f_plus_nominal = loaded_data["f_plus_nominal"]
        
        f_plus_uncertainty = loaded_data["f_plus_uncertainty"]
        f_minus_nominal = loaded_data["f_minus_nominal"]
        f_minus_uncertainty = loaded_data["f_minus_uncertainty"]
        phi_plus_nominal = loaded_data["phi_plus_nominal"]
        phi_plus_uncertainty = loaded_data["phi_plus_uncertainty"]
        phi_minus_nominal = loaded_data["phi_minus_nominal"]
        phi_minus_uncertainty = loaded_data["phi_minus_uncertainty"]
        Z_nominal = loaded_data["Z_nominal"]
        Z_uncertainty = loaded_data["Z_uncertainty"]
        W_T_nominal = loaded_data["W_T_nominal"]
        W_T_uncertainty = loaded_data["W_T_uncertainty"]
        start_time = loaded_data["start_time"]
        end_time = loaded_data["end_time"]
        temp = loaded_data["temp"]
        lf_center_freq  = loaded_data["lf_center_freq"]
        state = loaded_data["state"]
        E = loaded_data["E"]
        field_plate_amplitude = loaded_data["field_plate_amplitude"]
        electric_field_shift_MHz = loaded_data["electric_field_shift_MHz"]
        pulse_time_ms = loaded_data["pulse_time_ms"]
        wait_time_ms = loaded_data["wait_time_ms"]
        ramp_time_ms = loaded_data["ramp_time_ms"]
        rf_amplitude = loaded_data["rf_amplitude"]
        rf_duration_ms = loaded_data["rf_duration_ms"]
        results = np.array([
                    np.array([
                        ufloat(f_plus_nominal[i], f_plus_uncertainty[i]),
                        ufloat(f_minus_nominal[i], f_minus_uncertainty[i]),
                        start_time[i],
                        end_time[i],
                        temp[i],
                        ufloat(phi_plus_nominal[i], phi_plus_uncertainty[i]),
                        ufloat(phi_minus_nominal[i], phi_minus_uncertainty[i]),
                        lf_center_freq[i],
                        state[i],
                        E[i],
                        field_plate_amplitude[i],
                        electric_field_shift_MHz[i],
                        pulse_time_ms[i],
                        wait_time_ms[i],
                        ramp_time_ms[i],
                        rf_amplitude[i],
                        rf_duration_ms[i],
                        ufloat(Z_nominal[i], Z_uncertainty[i]),
                        ufloat(W_T_nominal[i], W_T_uncertainty[i])
                        ]) for i in range(len(f_plus_nominal))
                    ])
        col_indices = {'f+': 0,
            'f-': 1,
            'start_time': 2,
            'end_time': 3,
            'temp': 4,
            'phi0+': 5,
            'phi0-': 6,
            'lf_center_freq': 7,
            'state': 8,
            'E': 9,
            'field_plate_amplitude': 10,
            'electric_field_shift_MHz': 11,
            'pulse_time_ms': 12,
            'wait_time_ms': 13,
            'ramp_time_ms': 14,
            'rf_amplitude': 15,
            'rf_duration_ms': 16,
            'Z': 17,
            'W_T': 18,
            }

    return results, col_indices




# import numpy as np
# import os
# import matplotlib.pyplot as plt
# from onix.analysis.fitter import Fitter
# import onix.models.hyperfine as hyperfine
# import pandas
# from uncertainties import unumpy, ufloat
# from onix.data_tools import get_analysis_file_path
# from onix.analysis.functions.shared import data_identification_to_list, analysis_dnum

# """
# Shared analysis functions for any LF Ramsey spectroscopy. 
# """

# magnetic_field = 223e-4

# def averaging_ys(xs, ys):
#     """
#     Given multiple traces with the same phases this averages all traces into one. 
#     """
#     xs_unique = np.unique(xs)
#     ys_to_avg = [[] for _ in range(len(xs_unique))]
#     for x, y in zip(xs, ys):
#         ys_to_avg[np.argwhere(xs_unique == x)[0][0]].append(y)
#     ys_avg = []
#     ys_std = []
#     for y_list in ys_to_avg:
#         ys_avg.append(np.average(y_list))
#         ys_std.append(np.std(y_list))
#     ys_avg = np.array(ys_avg)
#     ys_std = np.array(ys_std)
    
#     return xs_unique, ys_avg, ys_std

# def phase_fit(phi, A, C, phi_0):
#     return A * np.cos(phi - phi_0) + C

# def get_phase_fitter(phases, heights, height_errs):
#     """
#     Given Ramsey data (phases, heights, and errors) this fits to a A cos(phi - phi_0) + C and returns the fitter.
#     """
#     fitter = Fitter(phase_fit)
#     fitter.set_data(phases, heights, height_errs)
#     fitter.set_bounds("A", 0, np.inf)

#     # setting this bound makes weird fits for certain phi_0's because they want to fit to a value outside the bound
#     # fitter.set_bounds("phi_0", 0, 2*np.pi)
#     fitter.fit()
#     return fitter

# def plot_ramsey(data, get_results, do_average = True):
#     """
#     Plot Ramsey fringes given the data dictionary. 
#     get_results will be specific to the detections we use (i.e. detect_1 - detect_2 vs detect_3 - detect_6)
#     get_results will be defined in the file specific functions file, so just pass get_results = get_results
#     """
#     index = []
#     fig, ax = plt.subplots(figsize = (10, 6), dpi = 120)
#     for ll, (label, data_range) in enumerate(data.items()):
#         headers, results_temp = get_results(data_range)
#         mask = np.ones(len(headers), dtype=bool)
#         for kk, header in enumerate(headers):
#             sequence = header["params"]["sequence"]["sequence"]
#             for name, repeat in sequence:
#                 if name.startswith("lf") and not name.endswith("piov2"):
#                     index.append(int(name.split("_")[-1]))
#                     break
#         xs = np.array([header["params"]["lf"]["phase_diffs"][index[kk]] for kk, header in enumerate(headers)])
#         if results_temp.ndim == 1:
#             ys = unumpy.nominal_values(results_temp)[1:]
#             errs = unumpy.std_devs(results_temp)[1:]
#             ax.errorbar(xs, ys, errs, label=label, marker='o', linestyle='')
#         else:
#             for kk in range(0, 2):
#                 ys = unumpy.nominal_values(results_temp[:, kk])
#                 errs = unumpy.std_devs(results_temp[:, kk])
#                 if do_average:
#                     xs_avg, ys_avg, errs_avg = averaging_ys(xs[mask], ys[mask])
#                 else:
#                     xs_avg, ys_avg, errs_avg = xs, ys, errs
#                 if kk == 0:
#                     lambda_label = ", $\\lambda = +1$"
#                 else:
#                     lambda_label = ", $\\lambda = -1$"
#                 ax.scatter(xs_avg, ys_avg, label=label + lambda_label, marker='o', linestyle='')
#                 fitter = get_phase_fitter(xs_avg, ys_avg, None)
#                 xs_fit = np.linspace(np.min(xs_avg), np.max(xs_avg), 100)
#                 ys_fit = fitter.fitted_value(xs_fit)
#                 ax.plot(xs_fit, ys_fit)
#                 if kk == 0:
#                     label_str = label + " $\\lambda = +1$ \n" + fitter.all_results_str()
#                     ax.text(0,1.02, label_str, transform = ax.transAxes)
#                 else:
#                     label_str = label + " $\\lambda = -1$ \n" + fitter.all_results_str()
#                     ax.text(0.3,1.02, label_str, transform = ax.transAxes)
#                 print(fitter.result_str("A"))
#                 print(fitter.result_str("C"))
#                 print(fitter.result_str("phi_0"))

#     ax.set_xlabel("Ramsey phase difference")
#     ax.set_ylabel("absorption - offset (arb. unit)")
#     ax.text(0.8,1.02,f"#{data_range[0]} - #{data_range[1]}" , transform = ax.transAxes)
#     ax.text(0.6,1.02, f"SNR = {round(fitter.results["A"]/fitter.errors["A"],2)}", transform = ax.transAxes)
#     ax.legend()
#     ax.grid()
#     plt.tight_layout()
#     plt.show()
#     print(f"SNR with 9 phase points = {fitter.results["A"]/fitter.errors["A"]}")


# ground = hyperfine.states["7F0"]
# ground._Hamiltonian = ground.H_total(magnetic_field)
# e_g, s_g = ground.energies_and_eigenstates()

# a_I_dot_n = (s_g[0].dag() * ground._I_x * s_g[0]).tr()
# abar_I_dot_n = (s_g[1].dag() * ground._I_x * s_g[1]).tr()
# b_I_dot_n = (s_g[2].dag() * ground._I_x * s_g[2]).tr()
# bbar_I_dot_n = (s_g[3].dag() * ground._I_x * s_g[3]).tr()
# I_a = (abar_I_dot_n - a_I_dot_n) / 2
# I_b = (bbar_I_dot_n - b_I_dot_n) / 2

# def combine_polarization_data(results):
#     def check_equal_and_append(check_from, check_name, append_to):
#         check_col = check_from[:, col_indices[check_name]]
#         count = np.unique(check_col)
#         if len(count) > 1:
#             raise Exception(f"{check_name} is not the same.")
#         append_to.append(check_col[0])

#     results_array = pandas.DataFrame.from_dict(results).to_numpy()
#     keys = list(results.keys())
#     indices = list(range(len(keys)))
#     col_indices = dict(zip(keys, indices))
#     data = {
#         "f+": [],
#         "f-": [],
#         "start_time": [],
#         "end_time": [],
#         "temp": [],
#         "phi0+": [],
#         "phi0-": [],
#     }
#     group_size = 2
#     for kk in range(len(results_array) // group_size):
#         sub_data = results_array[kk * group_size: kk * group_size + group_size]
#         data_indices = []
#         for name in results.keys():
#             if name not in ["start_time", "end_time", "D", "freq_center", "temp", "phi0"]:
#                 if name not in data:
#                     data[name] = []
#                 check_equal_and_append(sub_data, name, data[name])
#         for ll, datapoint in enumerate(sub_data):
#             if ll == 0:
#                 start_time = datapoint[col_indices["start_time"]]
#             if ll == len(sub_data) - 1:
#                 end_time = datapoint[col_indices["end_time"]]
#             if datapoint[col_indices["D"]]:
#                 f_p = datapoint[col_indices["freq_center"]]
#                 phi0_p = datapoint[col_indices["phi0"]]
#             else:
#                 f_m = datapoint[col_indices["freq_center"]]
#                 phi0_m = datapoint[col_indices["phi0"]]


#         data["f+"].append(f_p)
#         data["f-"].append(f_m)
#         data["phi0+"].append(phi0_p)
#         data["phi0-"].append(phi0_m)
#         data["start_time"].append(start_time)
#         data["end_time"].append(end_time)
#         data["temp"].append(np.nanmean(sub_data[:, col_indices["temp"]]))

#     data["f+"] = np.array(data["f+"])
#     data["f-"] = np.array(data["f-"])
#     data["phi0+"] = np.array(data["phi0+"])
#     data["phi0-"] = np.array(data["phi0-"])
#     data["Z"] = (data["f+"] + data["f-"]) / 4
#     data["W_T"] = []
#     for kk in range(len(data["f+"])):
#         if data["state"][kk] == "a":
#             I = I_a
#         else:
#             I = I_b
#         data["W_T"].append((data["f+"][kk] - data["f-"][kk]) / 4 / I)

#     keys = list(data.keys())
#     indices = list(range(len(keys)))
#     col_indices = dict(zip(keys, indices))
#     data = pandas.DataFrame.from_dict(data).to_numpy()
#     return data, col_indices

# def analyze_data(data_range, max, get_results, ignore_data_numbers = [], load_old = True, save_new = True):
#     """
#     Analyzes a collection of Ramsey phase scans. Again get_results depends on the specific sequence, so input get_results = get_results
#     load_old determines if this will search for the processed data and load it
#     save_new determines if this will save the processed data
#     """
#     points_per_scan = data_range[1] - data_range[0]
#     first = data_range[0]
#     last = max
#     first_unprocessed = first
#     all_old_data = False
#     all_new_data = True

#     loaded_data = None
#     path_to_save = get_analysis_file_path(analysis_dnum, f"{first}_{last}_processed.npz")
#     dir = os.path.dirname(path_to_save)
#     if load_old is True:
#         for file in os.listdir(dir):
#             try: 
#                 start_str, stop_str, _ = file.split("_")
#             except:
#                 continue
#             start = int(start_str)
#             stop = int(stop_str)
#             if start == data_range[0]:
#                 all_new_data = False
#                 if stop == max:
#                     all_old_data = True
#                 first_unprocessed = stop + 1
#                 old_data_path = os.path.join(dir, file)
#                 loaded_data = np.load(old_data_path, allow_pickle = True)
#                 print("Existing data loaded")
#                 break
        
#     current = first_unprocessed + points_per_scan
#     offset = 0
#     all_results = {
#         "lf_center_freq": [],
#         "freq_center": [],
#         "state": [],
#         "E": [],
#         "D": [],
#         "field_plate_amplitude": [],
#         "electric_field_shift_MHz": [],
#         "pulse_time_ms": [],
#         "wait_time_ms": [],
#         "ramp_time_ms": [],
#         "start_time": [],
#         "end_time": [],
#         "temp": [],
#         "rf_amplitude": [],
#         "rf_duration_ms": [],
#         "phi0": [],
#     }

#     if all_old_data is False:
#         while current + offset <= max:
#             data_range_now = (first_unprocessed + offset, first_unprocessed + points_per_scan + offset)
#             if data_range_now[0] in ignore_data_numbers:
#                 offset += 1
#                 continue
#             data_list = data_identification_to_list(data_range_now)
#             try:
#                 headers, results = get_results(
#                     data_range_now, 
#                     fitted_freq_offset = np.inf,
#                     fitted_amp_difference = np.inf,
#                     chi_cutoff = np.inf
#                 )
#                 if headers is None:
#                     offset += len(list(data_list))
#                     continue
#             except Exception as e:
#                 offset += len(list(data_list))
#                 print(e)
#                 continue
        
#             for header in headers:
#                 if "temp" not in header or header["temp"] is None:
#                     header["temp"] = np.nan
        
#             index = []
#             for header in headers:
#                 sequence = header["params"]["sequence"]["sequence"]
#                 for name, repeat in sequence:
#                     if name.startswith("lf") and not name.endswith("piov2"):
#                         index.append(int(name.split("_")[-1]))
#                         break
                        
#             center_freq = headers[0]["params"]["lf"]["center_frequency"].to("Hz").magnitude
#             pulse_time_ms = headers[0]["params"]["lf"]["piov2_time"].to("ms").magnitude
#             wait_time_ms = headers[0]["params"]["lf"]["wait_time"].to("ms").magnitude
#             total_time_ms = pulse_time_ms + wait_time_ms
#             detuning = headers[0]["params"]["lf"]["detuning"].to("Hz").magnitude
#             ramp_time = headers[0]["params"]["field_plate"]["ramp_time"].to("ms").magnitude
#             probe_freq = center_freq + detuning
#             fp_amplitude = headers[0]["params"]["field_plate"]["amplitude"]
#             stark_shift = headers[0]["params"]["field_plate"]["stark_shift"].to("MHz").magnitude
#             detect_detuning = headers[0]["params"]["detect"]["detunings"].to("MHz").magnitude
#             E_field = fp_amplitude > 0
#             phases = [header["params"]["lf"]["phase_diffs"][index[kk]] for kk, header in enumerate(headers)]
#             temp = np.nanmean([header["temp"] for header in headers])
#             rf_amplitude = headers[0]["params"]["rf"]["amplitude"]
#             rf_duration_ms = headers[0]["params"]["rf"]["HSH"]["T_ch"].to("ms").magnitude
        
#             for kk in range(2):  # positive and negative Stark components.
#                 ys = unumpy.nominal_values(results[:, kk])
#                 errs = unumpy.std_devs(results[:, kk])
#                 try:
#                     fitter = get_phase_fitter(phases, ys, None)
#                 except:
#                     break
#                 phi0 = ufloat(fitter.results["phi_0"], fitter.errors["phi_0"])
#                 phi0 = (np.pi + phi0) % (2 * np.pi) - np.pi
#                 freq_center = phi0 / (2 * np.pi) / (total_time_ms * 1e-3) + probe_freq
                
#                 neg_DdotE = kk == 0
#                 E = E_field
#                 D = (not neg_DdotE) == E
#                 epoch_times = (
#                     headers[0]["data_info"]["save_epoch_time"],
#                     headers[-1]["data_info"]["save_epoch_time"],
#                 )
#                 if probe_freq > 200e3:
#                     state = "a"
#                 else:
#                     state = "b"
#                 all_results["lf_center_freq"].append(center_freq)
#                 all_results["freq_center"].append(freq_center)
#                 all_results["state"].append(state)
#                 all_results["E"].append(E)
#                 all_results["D"].append(D)
#                 all_results["start_time"].append(epoch_times[0])
#                 all_results["end_time"].append(epoch_times[1])
#                 all_results["pulse_time_ms"].append(pulse_time_ms)
#                 all_results["wait_time_ms"].append(wait_time_ms)
#                 all_results["field_plate_amplitude"].append(fp_amplitude)
#                 all_results["electric_field_shift_MHz"].append(stark_shift)
#                 all_results["ramp_time_ms"].append(ramp_time)
#                 all_results["temp"].append(temp)
#                 all_results["rf_amplitude"].append(rf_amplitude)
#                 all_results["rf_duration_ms"].append(rf_duration_ms)
#                 all_results["phi0"].append(phi0)
            
#             offset += len(list(data_list))
#         new_results, col_indices = combine_polarization_data(all_results)

#         if loaded_data is None:
#             results = new_results
#         else:
#             results = np.concatenate((loaded_data["results"], new_results), axis = 0)

#         if all_new_data is False:
#             try:
#                 os.remove(old_data_path)
#             except:
#                 pass
#         if save_new:
#             np.savez(
#                 path_to_save,
#                 results=results,
#                 col_indices=col_indices,
#             )

#     else:
#         results = loaded_data["results"]
#         col_indices = loaded_data["col_indices"].tolist()

#     return results, col_indices
