# import matplotlib.pyplot as plt
import numpy as np
from uncertainties import unumpy
from tqdm import tqdm
import matplotlib.pyplot as plt
from copy import deepcopy
import datetime

from onix.units import ureg, Q_
from onix.data_tools import get_experiment_data
from onix.analysis.shared.fitter import get_fitter, two_peak_gaussian, cosx
from onix.helpers import present_float

# RAW DATA DICTIONARY KEYS
DATA_1_DEFAULT_NAME = "detect_1"
DATA_2_DEFAULT_NAME = "detect_2"
PHOTODIODE_1_DEFAULT_NAME = "transmission"
PHOTODIODE_2_DEFAULT_NAME = "monitor"

# I \cdot X
I_DOT_X_A = 1.48
I_DOT_X_B = 0.75
I_DOT_X_C = 0.05

# VALUES TO SAVE IN ANALYSIS FILES (ALSO USED FOR MASKS)
HEADER_LOC = {
    # FORMAT:
    # STRING NAME       : LIST OF NESTED KEYS IN HEADERS

    # CHASM
    "chasm_amplitude"   : ["params", "chasm", "amplitudes"],
    "chasm_duration"    : ["params", "chasm", "durations"],
    "chasm_repeats"     : ["params", "chasm", "repeats"],

    # ANTIHOLE
    "antihole_amplitude": ["params", "antihole", "amplitudes"],
    "antihole_duration" : ["params", "antihole", "durations"],
    "antihole_repeats"  : ["params", "antihole", "repeats"],

    # LF RAMSEY
    "center_frequency"  : ["params", "lf", "ramsey", "center_frequency"],
    "Sigma"             : ["params", "lf", "ramsey", "Sigma"],
    "piov2_time"        : ["params", "lf", "ramsey", "piov2_time"],
    "wait_time"         : ["params", "lf", "ramsey", "wait_time"],

    # FIELD PLATE
    "polarity"          : ["params", "field_plate", "polarity"],

    # DETECT
    "detect_amplitude"  : ["params", "detect", "abs", "amplitude"],
    "detect_repeats"    : ["params", "detect", "abs", "repeats"],

    # MISC
    "delay_time"        : ["params", "delay_time"],
    "data_number"       : ["data_info", "data_number"],
    "save_epoch_time"   : ["data_info", "save_epoch_time"],
}





class OpticalAnalysis:
    """
    Everything optical spectrum related.
    Args:
        data_number: the data number
        normalized: if true normalizes the transmission with monitors photodiode data; output is a single array
        optical_depth: if true returns -log(transmission)
        TODO: fix bugs when optical_depth false.
        TODO: implement when electric field off.
    """
    def __init__(self, data_number: int, normalized: bool = True, optical_depth: bool = True):
        if optical_depth == False:
            raise NotImplementedError("optical depth = False not implemented")

        self._data_number = data_number
        self._optical_depth = optical_depth
        self._data, self._headers = get_experiment_data(self._data_number)
        self._detunings = self._data["detunings_MHz"]
        self._optical_depths = self.get_optical_spectrum()
        
    def get_optical_spectrum(self):
        """
        Extract data from dictionary, average and return normalized, optical depth change.
        """
        normalized_detect_1 = self.get_raw_spectrum_average_normalized(DATA_1_DEFAULT_NAME)
        normalized_detect_2 = self.get_raw_spectrum_average_normalized(DATA_2_DEFAULT_NAME)
        
        if self._optical_depth:
            return -unumpy.log(normalized_detect_2/normalized_detect_1)
        else:
            return normalized_detect_2/normalized_detect_1
    
    def get_raw_spectrum_average_normalized(self, detect_name):
        """
        Extract data from dictionary and average, normalized between monitor and transmission photodiodes..
        """
        detect_transmission = self.get_raw_spectrum_average(detect_name, PHOTODIODE_1_DEFAULT_NAME)
        detect_monitor = self.get_raw_spectrum_average(detect_name, PHOTODIODE_2_DEFAULT_NAME)
        
        return detect_transmission/detect_monitor

    def get_raw_spectrum_average(self, detect_name, photodiode):
        """
        Extract data from dictionary and average.
        """
        detect_raw = self._data[photodiode][()][detect_name]
        detect_avg = np.average(detect_raw, axis=0)
        detect_err = np.std(detect_raw, axis=0)/np.sqrt(np.shape(detect_raw[0]))
        detect = unumpy.uarray(detect_avg, detect_err)
        return detect

    def fit_optical_spectrum(self, p0user: dict = None):
        """
        Fit the optical spectrum to two gaussians.
        """
        # initial fit guess
        field_plate = self._headers["params"]["field_plate"]
        stark_shift = (field_plate["high_voltage"]*field_plate["amplifier_voltage_gain"]*field_plate["voltage_to_field"]*field_plate["dipole_moment"]).to("MHz").magnitude
        p0 = {
            "f1": -stark_shift, 
            "f2": stark_shift, 
            "a1": -0.01,
            "a2": -0.01,
            "sigma1": 1, 
            "sigma2": 1,
            "b": 0,
            "c": 0,
        }
        
        # overwrite initial guess with user's guess
        if p0user is not None:
            p0.update(p0user)

        min_detuning = min(self._detunings)
        max_detuning = max(self._detunings)
        bounds = {
            "f1": [min_detuning, 0],
            "f2": [0, max_detuning],
            "a1": [-np.inf, np.inf],
            "a2": [-np.inf, np.inf],
            "sigma1": [0, (max_detuning - min_detuning)],
            "sigma2": [0, (max_detuning - min_detuning)],
            "c": [-np.inf, np.inf],
        }

        fitter = get_fitter(
            two_peak_gaussian, 
            self._detunings, 
            unumpy.nominal_values(self._optical_depths), 
            unumpy.std_devs(self._optical_depths), 
            p0=p0,
            bounds=bounds)

        return fitter

    def get_fit_peaks(self):
        """
        Get a1 and a2 from the two gaussian fit.
        """
        fitter = self.fit_optical_spectrum()

        return fitter.results["a1"], fitter.results["a2"]

    def plot_optical_spectrum_data(self, ax, fitit: bool = True):
        """
        Plot optical depth vs optical detuning.
        """
        ax.errorbar(self._detunings, unumpy.nominal_values(self._optical_depths), unumpy.std_devs(self._optical_depths), ls="", fmt=".",)
        if fitit:
            fitter = self.fit_optical_spectrum()
            xs_fit = np.linspace(np.min(self._detunings), np.max(self._detunings), 1000)
            ys_fit = fitter.fitted_value(xs_fit)
            ax.plot(xs_fit, ys_fit)

        return ax

    def plot_raw_optical_spectrum_data(self, ax, detect_name):
        """
        Plot raw optical depth vs optical detuning.
        """
        raw_optical_depths = -unumpy.log(self.get_raw_spectrum_average_normalized(detect_name))
        ax.errorbar(self._detunings, unumpy.nominal_values(raw_optical_depths), unumpy.std_devs(raw_optical_depths), label=detect_name, ls="", fmt=".",)
        return ax

    def plot_optical_spectrum_params(self, ax):
        """
        Plot axes, grid,
        """
        ax.set_xlabel(r"Optical detuning, $\nu_\mathrm{opt}$ (MHz)")
        ax.set_ylabel(r"Optical depth change, $\Delta$OD")
        ax.grid(alpha=.1)
        return ax





class ScanAnalysis:
    # TODO: change name; not necessarily "frequency" related
    def __init__(self, data_numbers: list | np.ndarray | tuple):
        """
        Takes list, array or tuple of data_numbers. If two valued tuple, considers entire range between two values.
        Data_
        """
        if isinstance(data_numbers, list):
            data_numbers = np.array(data_numbers)
        elif isinstance(data_numbers, np.ndarray):
            pass
        elif isinstance(data_numbers, tuple) and len(data_numbers) == 2:
            data_numbers = np.array(list(range(data_numbers[0], data_numbers[1]+1)))
        else:
            raise NotImplementedError("Must be list or ndarray or tuple with 2 values.")

        # shave down data_numbers to acceptable range (0 to len-len%packet_size)
        self._data_numbers = data_numbers #[0:len(data_numbers) - len(data_numbers) % data_packet_size]

        self._optical_depths_pi_m1, self._optical_depths_pi_p1, self._headers = self.get_fits()

    def get_fits(self):
        """
        Obtain optical depth fits of data_numbers list. Returns optical depths for + and -.
        Note a1 corresponds to freq < 0, a2 corresponds to freq > 0.
        """
        a1s = []
        a2s = []
        headers = []
        
        for data_number in self._data_numbers:
            optical_data = OpticalAnalysis(data_number)
            a1, a2 = optical_data.get_fit_peaks()
            a1s.append(a1)
            a2s.append(a2)
            headers.append(optical_data._headers)

        a1s = np.array(a1s)
        a2s = np.array(a2s)

        return a1s, a2s, headers

    def _get_nested_dict_val(self, scan_dict, scan_list):
        """
        Get value in nested dictionary using the nested keys in scan_list.
        """
        for step in scan_list:
            scan_dict = scan_dict[step]
        return scan_dict

    def get_list_from_header(self, scan_list):
        """
        Get a list of scanned values from headers of the data_numbers using the scan_list to define a parameter key.
        """
        # check very first data_number's scanned object; must be an object that is a single quant.
        first_scanned_val = self._get_nested_dict_val(self._headers[0]["params"], scan_list)
        if isinstance(first_scanned_val, (list, np.ndarray)):
            raise NotImplementedError("Scan single quantities.")
        xaxis = []
        unit = 1
        for header in self._headers:
            scanned_val = self._get_nested_dict_val(header["params"], scan_list)
            if isinstance(scanned_val, Q_):
                unit = scanned_val.units
                scanned_val = scanned_val.magnitude
            xaxis.append(scanned_val)
        return np.array(xaxis) * unit
    
    ## FOR PHASE SCAN
    def fit_phase_scan(self):
        """
        Specifically fit a phase scan.
        """
        scan_list = ["lf", "ramsey", "phase"]
        if scan_list[0] == scan_list[1]:
            raise ValueError("This is not a phase scanned data number range.")
        
        xaxis = self.get_list_from_header(scan_list)

        fitter = get_fitter(
            cosx, 
            xaxis, 
            self._optical_depths_pi_m1
        )
        phi_pi_m1 = self.wrap_phase(fitter.results["x0"])

        fitter = get_fitter(
            cosx, 
            xaxis, 
            self._optical_depths_pi_p1
        )
        phi_pi_p1 = self.wrap_phase(fitter.results["x0"])
        return phi_pi_m1, phi_pi_p1
    
    def wrap_phase(self, phases):
        """
        Keep phase within bound
        """
        phases_wrapped = (phases + np.pi) % (2 * np.pi) - np.pi
        return phases_wrapped  
     
    def phase_to_frequency(self, phi0, ramsey_time, probe_freq):
        """
        First order calculation of the frequency center based on the phase offset fitted by a phase scan.
        """
        freq_center = phi0 / (2 * np.pi * ramsey_time) + probe_freq
        return freq_center
    
    def get_frequency_center(self):
        """
        Get frequency center from phase scan.
        """
        ramsey_params = self._headers[0]["params"]["lf"]["ramsey"]
        probe_freq = ramsey_params["center_frequency"] + ramsey_params["detuning"] + ramsey_params["Sigma"]*ramsey_params["Zeeman_shift_along_b"]
        ramsey_time = ramsey_params["wait_time"] + ramsey_params["piov2_time"]
        phi_pi_m1, phi_pi_p1 = self.fit_phase_scan()
        f_pi_m1 = self.phase_to_frequency(phi_pi_m1, ramsey_time, probe_freq)
        f_pi_p1 = self.phase_to_frequency(phi_pi_p1, ramsey_time, probe_freq)
        return f_pi_m1.to("Hz").magnitude, f_pi_p1.to("Hz").magnitude, self._headers[0]

    ### PLOTTING GENERIC SWEEP
    def plot_sweep_data(self, ax, scan_list, label="", **kwargs):
        """
        Plot the sweep from get_list_from_header() using arbitrary scanned 
        parameter defined in the scan_list.
        scan_list: list of nested dictionary keys for parameter, e.g. ["rf", "rabi", "detuning"]
        """
        xaxis = self.get_list_from_header(scan_list)
    
        # FOR AXIS LABELS
        xaxis_name = " ".join(scan_list)
        if isinstance(xaxis, Q_):
            xaxis_units = xaxis.units
            xaxis = xaxis.magnitude
        else:
            xaxis_units = "dimensionless"

        # EXCEPTION TO UNITS
        if scan_list[-1] == "phase":
            xaxis_units = "rad"

        # capitalize these words in axis labels
        capitalize_strings = ["lf", "rf"]
        for capitalize_string in capitalize_strings:
            if capitalize_string in xaxis_name:
                xaxis_name.replace(capitalize_string, capitalize_string.upper())

        # PLOT
        ax.scatter(xaxis, self._optical_depths_pi_m1, label=f"{label} $\\Pi = -1$", **kwargs)
        ax.scatter(xaxis, self._optical_depths_pi_p1, label=f"{label} $\\Pi = +1$", **kwargs)

        ax.set_xlabel(f"{xaxis_name} ({xaxis_units})")
        ax.set_ylabel(r"Optical depth change, $\Delta$OD")
        ax.grid(alpha=.1)
        ax.legend()
        return ax
    




class TimeSeriesAnalysis:
    # TODO: get_scanned_data output compatible with saving/loading data sets
    # TODO: 
    def __init__(self, data_numbers: list | np.ndarray | tuple, data_packet_size: int = 8):
        """
        Compute time series phase fits, then plot time series center frequencies and perform T-violation calculation (computing Z, W).
        """
        if isinstance(data_numbers, list):
            data_numbers = np.array(data_numbers)
        elif isinstance(data_numbers, np.ndarray):
            pass
        elif isinstance(data_numbers, tuple) and len(data_numbers) == 2:
            if data_numbers[1] < data_numbers[0]:
                raise ValueError("First data number exceeds second data number in range.")
            data_numbers = np.array(list(range(data_numbers[0], data_numbers[1]+1)))
        else:
            raise NotImplementedError("Input data_numbers must be one of type: list, ndarray, or 2-tuple with start and end value.")
        
        # Strip end of data numbers to make integer multiple of data_packet_size
        self._data_numbers = data_numbers[0:len(data_numbers) - len(data_numbers) % data_packet_size]
        self._data_packet_size = data_packet_size

        # Break down data numbers into groups of data packets with size data_packet_size
        self._data_numbers_list = [data_numbers[i:i+data_packet_size] for i in range(0, len(self._data_numbers), data_packet_size)]

        self._pis =  ["+1", "-1"]

        # Get data and compute Z, W.
        self._data = self.get_scanned_data()
        self._append_Z()
        self._append_W()

        # Unique scans
        self._unique_scan = self.get_unique_scan()

    def _get_nested_dict_val(self, scan_dict, scan_list):
        """
        Get value in nested dictionary using the nested keys in scan_list.
        """
        for step in scan_list:
            scan_dict = scan_dict[step]
        return scan_dict

    def get_unique_scan(self):
        unique_scan = {}
        header_loc = HEADER_LOC
        for name in header_loc.keys():
            if name not in ["data_number", "save_time", "save_epoch_time"]:
                unique_scan[name] = np.unique(self._data[name])
        return unique_scan

    def get_scanned_data(self):
        """
        Get time domain data using the frequency center analysis from ScanAnalysis with phase scans.
        """

        # Prepare dictionary to save data
        header_loc = HEADER_LOC
        data = {"f": {"+1": [], "-1": []}}
        units = {}
        for name in header_loc.keys():
            data[name] = []
            units[name] = 1

        # Append values from ScanAnalysis to dictionary for each data packet of size data_packet_size
        for data_numbers_packet in tqdm(self._data_numbers_list):

            # Get frequency centers and headers for each phase scan of a data packet
            scan_analysis = ScanAnalysis(data_numbers_packet)
            f_pi_m1, f_pi_p1, header = scan_analysis.get_frequency_center()

            # Append Pi+ and Pi- frequency centers to data dictionary
            data["f"]["+1"].append(f_pi_p1)
            data["f"]["-1"].append(f_pi_m1)

            # Go through each value in HEADER_LOC and save values
            for name, location_list in header_loc.items():
                # Get value, strip units, append to data dictionary
                quantity_from_header = self._get_nested_dict_val(header, location_list)
                if isinstance(quantity_from_header, Q_):
                    unit = quantity_from_header.units
                    quantity_from_header = quantity_from_header.magnitude
                    units[name] = unit
                data[name].append(quantity_from_header)

        # Convert to ndarray and add units back
        for Pi in self._pis:
            data["f"][Pi] = np.array(data["f"][Pi])
        for name in header_loc.keys():
            data[name] = np.array(data[name]) #* units[name] (leaving units off for now)

        return data

    def _append_Z(self):
        """
        Append Z to self._data
        """
        self._data["Z"] = (self._data["f"]["+1"] + self._data["f"]["-1"])/4
    
    def _append_W(self, state: str = "b"):
        """
        Append W to self._data
        """
        if state == "a":
            I_dot_x = I_DOT_X_A
        elif state == "b":
            I_dot_x = I_DOT_X_B
        elif state == "c": 
            I_dot_x = I_DOT_X_C
        else:
            raise ValueError("State does not exist.")
        self._data["W"] = self._data["polarity"]*(self._data["f"]["+1"] - self._data["f"]["-1"])/(4 * I_dot_x)
    
    def get_filtered_data(self, filter=None):
        data = deepcopy(self._data)
        if filter is not None:
            if np.all(filter == False):
                    raise ValueError("Invalid filter applied. All elements are False.")
            for name in data.keys():
                if name != "f":
                    data[name] = data[name][filter]
                else:
                    # exception is "f" stored in data["f"]["+1"] and data["f"]["-1"]
                    for Pi in self._pis:
                        data[name][Pi] = data[name][Pi][filter]
        return data
    
    def subplots(self, filter=None):
        """
        Plot with a filter.
        """
        # If filter applied then replace data dictionary with filtere dictionary.
        data = self.get_filtered_data(filter)
        
        Sigmas = np.unique(data["Sigma"]) # ["+1"] or ["-1"] or ["+1", "-1"]
        sn = len(Sigmas) # 1 or 2

        fig, ax = plt.subplots(figsize=(12, 9), 
                               nrows=2+sn, 
                               ncols=2, 
                               gridspec_kw=
                               {
                                   "width_ratios":[4, 1], 
                                   "hspace": 0, 
                                   "wspace": 0
                               }, 
                               sharex="col", 
                               sharey="row")

        # Histogram bin size
        bins = int(np.sqrt(len(data["f"]["+1"])))

        # Plot colors for Pi = +/- 1
        colors_12 = ["C0", "C1"]

        # Plot colors for Sigma = +/- 1
        colors_34 = ["C2", "C3"]

        for i, Sigma in enumerate(Sigmas):
            # times
            ts = data["save_epoch_time"][data["Sigma"] == Sigma] - data["save_epoch_time"][0]

            # frequency center plot
            for j, Pi in enumerate(self._pis):
                fs = data["f"][Pi][data["Sigma"] == Sigma]
                ax[i, 0].scatter(ts, fs, label=f"$\Pi$ = {Pi}", color=colors_12[j])
                ax[i, 1].hist(fs, bins=bins, orientation="horizontal", alpha=0.5, color=colors_12[j])

            # Z plot
            Zs = data["Z"][data["Sigma"] == Sigma]
            ax[sn, 0].scatter(ts, Zs, label=f"$\Sigma$ = {Sigma}", color=colors_34[i])
            ax[sn, 1].hist(Zs, bins=bins, orientation="horizontal", alpha=0.5, color=colors_34[i])

            # W plot
            Ws = data["W"][data["Sigma"] == Sigma]
            ax[sn+1, 0].scatter(ts, Ws, label=f"$\Sigma$ = {Sigma}", color=colors_34[i])
            ax[sn+1, 1].hist(Ws, bins=bins, orientation="horizontal", alpha=0.5, color=colors_34[i])

            ax[i, 0].set_ylabel(f"$f(\Pi=\pm 1, \Sigma = {Sigma})$")

        # Change y-axis label depending on # unique Sigmas
        if len(Sigmas) > 1:
            sigmas_str = "$\pm 1$"
        else:
            sigmas_str = Sigmas[0]
        ax[sn  , 0].set_ylabel("$\mathcal{Z}(\Sigma = $" + f"{sigmas_str}" +"$)$")
        ax[sn+1, 0].set_ylabel("$\mathcal{W}(\Sigma = $" + f"{sigmas_str}" +"$)$")

        ax[sn+1, 0].set_xlabel("Time from start (s)")

        # Settings for each row
        for row in range(sn+2):
            ax[row, 0].legend()
            ax[row, 1].spines['top'].set_visible(False)
            ax[row, 1].spines['right'].set_visible(False)
            ax[row, 1].spines['bottom'].set_visible(False)
            # ax[row, 1].spines['left'].set_visible(False)
            ax[row, 1].get_xaxis().set_ticks([])
            # ax[row, 1].get_yaxis().set_ticks([])
            ax[row, 1].ticklabel_format(useOffset=False)

        return fig, ax
    
    def get_info_pi_sigma(self, data, Pi, Sigma):
        fs = data["f"][Pi][data["Sigma"] == Sigma]
        info = {
            "fs_avg" : np.average(fs),
            "fs_ste" : np.std(fs)/np.sqrt(len(fs)),
        }
        return info
    
    def get_info_sigma(self, data, Sigma):
        if Sigma is not None:
            Ws = data["W"][data["Sigma"] == Sigma]
            Zs = data["Z"][data["Sigma"] == Sigma]
        else:
            Ws = data["W"]
            Zs = data["Z"]
        info = {
            "W_avg" : np.average(Ws),
            "W_ste" : np.std(Ws)/np.sqrt(len(Ws)),
            "Z_avg" : np.average(Zs),
            "Z_ste" : np.std(Zs)/np.sqrt(len(Zs)),
        }
        return info
    
    def get_info_generic(self, data):
        exp_time = data["save_epoch_time"][-1]- data["save_epoch_time"][0]
        if exp_time < 60:
            new_exp_time = exp_time
            units = "sec"
        elif exp_time >= 60 and exp_time < 3600:
            new_exp_time = exp_time/60
            units = "min"
        elif exp_time >= 3600:
            new_exp_time = exp_time/3600
            units = "h"
        info = {
            "Date" : datetime.datetime.fromtimestamp(data["save_epoch_time"][0]).strftime('%c'),
            "Total experiment time" : f"{new_exp_time:.2f} {units}",
            "First data number" : data["data_number"][0],
            "Last data number" : data["data_number"][-1] + self._data_packet_size - 1,
            "Packet size" : self._data_packet_size,
        }
        return info
    
    def print_info(self, filter=None):
        data = self.get_filtered_data(filter)
        info_generic = self.get_info_generic(data)

        separator = "\n"+"-="*30+"\n"

        print(separator)

        for key, value in info_generic.items():
            print(key.ljust(25), " : ", value)
        
        print(separator)

        for Sigma in np.unique(data["Sigma"]):
            for Pi in self._pis:
                info_pi_sigma = self.get_info_pi_sigma(data, Pi, Sigma)
                print(f"f(Π = {Pi}, Σ = {Sigma})", f" = {present_float(info_pi_sigma['fs_avg'], info_pi_sigma['fs_ste'], digits=2)} Hz")

        print(separator)

        for Sigma in np.unique(data["Sigma"]):
            info_sigma = self.get_info_sigma(data, Sigma)
            print(f"Z(Σ = {Sigma}) = {present_float(info_sigma['Z_avg'], info_sigma['Z_ste'], digits=2)} Hz")
            print(f"W(Σ = {Sigma}) = {present_float(info_sigma['W_avg'], info_sigma['W_ste'], digits=2)} Hz")

        print(separator)

        exp_time = data["save_epoch_time"][-1]- data["save_epoch_time"][0]
        info_sigma = self.get_info_sigma(data, None)
        print(f"Z = {present_float(info_sigma['Z_avg'], info_sigma['Z_ste'], digits=2)} Hz")
        print(f"W = {present_float(info_sigma['W_avg'], info_sigma['W_ste'], digits=2)} Hz")
        print(f"S = {info_sigma['W_ste']*np.sqrt(exp_time/3600)*1e3:.1f} mHz rt-hr")

        print(separator)

        # def allen_deviation(self, ax):
        #     ts = self._data["s"]
        #     times = results[:, col_indices["start_time"]].astype(float)
        #     taus = np.logspace(0, np.log10(len(times)) * 3, 500)
        #     total_time = times[-1] - times[0]

        #     allan_variables = [
        #         ("$f_b (D=+1)$", unumpy.nominal_values(results[:, col_indices["f+"]])),
        #         ("$f_b (D=-1)$", unumpy.nominal_values(results[:, col_indices["f-"]])),
        #         ("$f_b (D=+1, E=+1)$", unumpy.nominal_values(results[results[:, col_indices["E"]] == True, col_indices["f+"]])),
        #         ("$f_b (D=-1, E=+1)$", unumpy.nominal_values(results[results[:, col_indices["E"]] == True, col_indices["f-"]])),
        #         ("$f_b (D=+1, E=-1)$", unumpy.nominal_values(results[results[:, col_indices["E"]] == False, col_indices["f+"]])),
        #         ("$f_b (D=-1, E=-1)$", unumpy.nominal_values(results[results[:, col_indices["E"]] == False, col_indices["f-"]])),
        #         (
        #             "$\\Delta f_b (D=\\pm1, E=+1)$",
        #             unumpy.nominal_values(
        #                 results[results[:, col_indices["E"]] == True, col_indices["f+"]]
        #                 - results[results[:, col_indices["E"]] == True, col_indices["f-"]]
        #             )
        #         ),
        #         (
        #             "$\\Delta f_b (D=\\pm1, E=-1)$",
        #             unumpy.nominal_values(
        #                 results[results[:, col_indices["E"]] == False, col_indices["f+"]]
        #                 - results[results[:, col_indices["E"]] == False, col_indices["f-"]]
        #             )
        #         ),
        #         ("$W_T$", unumpy.nominal_values(results[:, col_indices["W_T"]])),
        #     ]
        #     step_sizes = [total_time / len(kk[1]) for kk in allan_variables]

        #     fig, ax = plt.subplots(figsize=(10, 6))
        #     for kk, (label, variable) in enumerate(allan_variables):
        #         try:
        #             real_taus, allan, allan_err, _ = mdev(variable, data_type="freq", taus=taus)
        #             real_taus *= step_sizes[kk]
        #             ax.errorbar(real_taus, allan, allan_err, label=label, ls="none", fmt="o")
        #         except:
        #             print("Cannot plot ", label)
        #             continue
        #     ax.set_xscale("log")
        #     ax.set_yscale("log")
        #     ax.grid()
        #     ax.legend()
        #     ax.set_xlabel("Averaging time (s)")
        #     ax.set_ylabel("Allan deviation (Hz)")
        #     ax.text(0,1.02, f"#{data_range[0]} - #{max}", transform = ax.transAxes)
        #     plt.show()