# import matplotlib.pyplot as plt
import numpy as np
from uncertainties import unumpy
from tqdm import tqdm
import matplotlib.pyplot as plt

from onix.units import ureg, Q_
from onix.data_tools import get_experiment_data
from onix.analysis.shared.fitter import get_fitter, two_peak_gaussian, cosx
from onix.helpers import present_float

# RAW DATA DICTIONARY KEYS
DATA_1_DEFAULT_NAME = "detect_1"
DATA_2_DEFAULT_NAME = "detect_2"
PHOTODIODE_1_DEFAULT_NAME = "transmission"
PHOTODIODE_2_DEFAULT_NAME = "monitor"

# I \cdot x for a and b state
I_DOT_X_A = 1.48
I_DOT_X_B = 0.75

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
        Plot optical depth vs optical detuning.
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
    def __init__(self, data_numbers: list | np.ndarray | tuple, data_packet_size: int = 8):
        """
        Compute time series phase fits, then plot time series center frequencies and perform T-violation calculation (computing Z, W).
        """
        if isinstance(data_numbers, list):
            data_numbers = np.array(data_numbers)
        elif isinstance(data_numbers, np.ndarray):
            pass
        elif isinstance(data_numbers, tuple) and len(data_numbers) == 2:
            data_numbers = np.array(list(range(data_numbers[0], data_numbers[1]+1)))
        else:
            raise NotImplementedError("Must be list or ndarray or tuple with 2 values.")
        
        self._data_numbers = data_numbers[0:len(data_numbers) - len(data_numbers) % data_packet_size]
        self._data_packet_size = data_packet_size

        # break down data numbers into groups of data packets with size data_packet_size
        self._data_numbers_list = [data_numbers[i:i+data_packet_size] for i in range(0, len(self._data_numbers), data_packet_size)]
                        

        self._fs_pi_sigma, self._headers = self.get_scanned_data()
        self._sigmas = [key for key in self._fs_pi_sigma.keys() if self._fs_pi_sigma[key]["+1"].size > 0]
        self._pis = ["+1", "-1"]

        self._Zs_sigma = self.get_Z()
        self._Ws_sigma = self.get_W()
        
    def get_scanned_data(self):
        """
        Get time domain data using the frequency center analysis from ScanAnalysis with phase scans.
        """
        f_pi_m1_sigma_m1 = []
        f_pi_p1_sigma_m1 = []
        f_pi_m1_sigma_p1 = []
        f_pi_p1_sigma_p1 = []
        electric_fields = []
        headers_sigma_p1 = []
        headers_sigma_m1 = []

        for data_numbers_packet in tqdm(self._data_numbers_list):
            scan_analysis = ScanAnalysis(data_numbers_packet)
            f_pi_m1, f_pi_p1, header = scan_analysis.get_frequency_center()
            sigma = header["params"]["lf"]["ramsey"]["Sigma"]
            if sigma <= 0:
                f_pi_m1_sigma_m1.append(f_pi_m1)
                f_pi_p1_sigma_m1.append(f_pi_p1)
                headers_sigma_m1.append(header)
            else:
                f_pi_m1_sigma_p1.append(f_pi_m1)
                f_pi_p1_sigma_p1.append(f_pi_p1)
                headers_sigma_p1.append(header)
        
        # first label: pi, second label: sigma (alphabetical)
        fs_pi_sigma = {
            # sigma = +/- 1
            "-1": { # pi = +/- 1
                "-1": np.array(f_pi_m1_sigma_m1),
                "+1": np.array(f_pi_p1_sigma_m1)
            },
            "+1": { # pi = +/- 1
                "-1": np.array(f_pi_m1_sigma_p1),
                "+1": np.array(f_pi_p1_sigma_p1)
            }
        }
        headers = {
            "-1": np.array(headers_sigma_m1),
            "+1": np.array(headers_sigma_p1),
        }

        return fs_pi_sigma, headers

    def get_Z(self):
        """
        Get Z for Sigma = +1 and Sigma = -1 individually.
        """
        Zs_sigma = {
            "-1": [],
            "+1": [],
        }

        for Sigma in self._sigmas:
            Zs_sigma[Sigma] = (self._fs_pi_sigma[Sigma]["+1"] + self._fs_pi_sigma[Sigma]["-1"])/4

        return Zs_sigma
        
    def get_W(self, state: str = "b"):
        """
        Get W for Sigma = +1 and Sigma = -1 individually.
        """
        if state == "a":
            I_dot_x = I_DOT_X_B
        elif state == "b":
            I_dot_x = I_DOT_X_B
        else:
            raise ValueError("No such state.")
        
        Ws_sigma = {
            "-1": [],
            "+1": [],
        }

        for Sigma in self._sigmas:
            polarities = np.array([header["params"]["field_plate"]["polarity"] for header in self._headers[Sigma]])
            Ws_sigma[Sigma] = polarities*(self._fs_pi_sigma[Sigma]["+1"] - self._fs_pi_sigma[Sigma]["-1"])/(4 * I_dot_x)

        return Ws_sigma
    
    def subplots(self):
        sn = len(self._sigmas)
        fig, ax = plt.subplots(figsize=(12, 9), 
                               nrows=2 + sn, 
                               ncols=2, 
                               gridspec_kw=
                               {
                                   "width_ratios":[4, 1], 
                                   "hspace": 0, 
                                   "wspace": 0
                               }, 
                               sharex="col", 
                               sharey="row")
        
        # time axis
        times = {}
        for Sigma in self._sigmas:
            times[Sigma] = np.array([header["data_info"]["save_epoch_time"] for header in self._headers[Sigma]])
        min_time = min([times[Sigma][0] for Sigma in self._sigmas])
        for Sigma in self._sigmas:
            times[Sigma] = times[Sigma] - min_time

        # ok bin size
        bins = int(np.sqrt(len(times[self._sigmas[0]])))

        colors_12 = ["C0", "C1"]
        colors_34 = ["C2", "C3"]
        for i, Sigma in enumerate(self._sigmas):

            # frequency center plot
            for j, Pi in enumerate(self._pis):
                ax[i, 0].scatter(times[Sigma], self._fs_pi_sigma[Sigma][Pi], label=f"$\Pi$ = {Pi}", color=colors_12[j])
                ax[i, 1].hist(self._fs_pi_sigma[Sigma][Pi], bins=bins, orientation="horizontal", alpha=0.5, color=colors_12[j])

            # Z plot
            ax[sn, 0].scatter(times[Sigma], self._Zs_sigma[Sigma], label=f"$\Sigma$ = {Sigma}", color=colors_34[i])
            ax[sn, 1].hist(self._Zs_sigma[Sigma], bins=bins, orientation="horizontal", alpha=0.5, color=colors_34[i])

            # W plot
            ax[sn+1, 0].scatter(times[Sigma], self._Ws_sigma[Sigma], label=f"$\Sigma$ = {Sigma}", color=colors_34[i])
            ax[sn+1, 1].hist(self._Ws_sigma[Sigma], bins=bins, orientation="horizontal", alpha=0.5, color=colors_34[i])
        
            ax[i, 0].set_ylabel(f"$f(\Pi=\pm 1, \Sigma = {Sigma})$")


        if len(self._sigmas) > 1:
            sigmas_str = "$\pm 1$"
        else:
            sigmas_str = self._sigmas[0]
        ax[sn  , 0].set_ylabel("$\mathcal{Z}(\Sigma = $" + f"{sigmas_str}" +"$)$")
        ax[sn+1, 0].set_ylabel("$\mathcal{W}(\Sigma = $" + f"{sigmas_str}" +"$)$")
        ax[sn+1, 0].set_xlabel("Time from start (s)")

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
    
    def get_info_pi_sigma(self, Pi, Sigma):
        fs = self._fs_pi_sigma[Sigma][Pi]
        info = {
            "fs_avg" : np.average(fs),
            "fs_ste" : np.std(fs)/np.sqrt(len(fs)),
        }
        return info
    
    def get_info_sigma(self, Sigma):
        Ws = self._Ws_sigma[Sigma]
        Zs = self._Zs_sigma[Sigma]
        info = {
            "W_avg" : np.average(Ws),
            "W_ste" : np.std(Ws)/np.sqrt(len(Ws)),
            "Z_avg" : np.average(Zs),
            "Z_ste" : np.std(Zs)/np.sqrt(len(Zs)),
        }
        return info
    
    def get_info_generic(self):
        info = {
            "Date" : self._headers[self._sigmas[0]][0]["data_info"]["save_time"],
            "Total experiment time" : self._headers[self._sigmas[0]][-1]["data_info"]["save_epoch_time"] - self._headers[self._sigmas[0]][0]["data_info"]["save_epoch_time"],
            "First data number" : self._data_numbers_list[0][0],
            "Last data number" : self._data_numbers_list[-1][-1],
            "Packet size" : self._data_packet_size,
        }
        return info
    
    def print_info(self):
        separator = "-="*20

        print(separator)

        info_generic = self.get_info_generic()
        for key, value in info_generic.items():
            print(key, ": ", value)
        
        print(separator)

        for Sigma in self._sigmas:
            for Pi in self._pis:
                info_pi_sigma = self.get_info_pi_sigma(Pi, Sigma)
                print(f"f(Π = {Pi}, Σ = {Sigma}) = {present_float(info_pi_sigma['fs_avg'], info_pi_sigma['fs_ste'], digits=2)} Hz")

        print(separator)

        for Sigma in self._sigmas:
            info_sigma = self.get_info_sigma(Sigma)
            print(f"Z(Σ = {Sigma}) = {present_float(info_sigma['Z_avg'], info_sigma['Z_ste'], digits=2)} Hz")
            print(f"W(Σ = {Sigma}) = {present_float(info_sigma['W_avg'], info_sigma['W_ste'], digits=2)} Hz")

        print(separator)