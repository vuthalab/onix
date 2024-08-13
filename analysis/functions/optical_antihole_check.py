import matplotlib.pyplot as plt
import numpy as np
from onix.data_tools import get_experiment_data
from onix.analysis.fitter import Fitter
from onix.analysis.helper import group_and_average_data
import pprint
import pint

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
    fitter.fit(maxfev = 1000000)
    return fitter

def plot_raw_data(data, label = None, note = None):
    """
    Plot the raw voltages from the transmission and monitor photodiodes. 
    """
    fig, ax = plt.subplots(1, 2, figsize = (12, 5))
    if isinstance(data, int):
        data_numbers = [data]
    elif isinstance(data, tuple):
        data_numbers = range(data[0], data[1]+1)
    elif isinstance(data, list):
        data_numbers = data

    if len(data_numbers) == 1:
        transmission_data = get_plotting_data(data_numbers[0], normalize=False, fitit=False, return_monitor = False) 
        for i, label in enumerate(transmission_data[0]):
            ax[0].scatter(transmission_data[1][i], transmission_data[2][i], label=f"{data_numbers[0]} - {label}")

        monitor_data = get_plotting_data(data_numbers[0], normalize=False, fitit=False, return_monitor = True)
        for i, label in enumerate(monitor_data[0]):
            ax[1].scatter(monitor_data[1][i], monitor_data[2][i], label=f"{data_numbers[0]} - {label}")
    else:        
        colors = [f"C{i}" for i in range(10)]
        markers = [".","x","o","+","s""v","^","<",">",",","1","2","3","4","8","p","P","h","H"]
        for j, data_number in enumerate(data_numbers):
            transmission_data = get_plotting_data(data_number, normalize=False, fitit=False, return_monitor = False) 
            for i, label in enumerate(transmission_data[0]):
                color = colors[j]
                marker = markers[i]
                ax[0].scatter(transmission_data[1][i], transmission_data[2][i], label=f"{data_number} - {label}", color=color, marker=marker)
    
        for j, data_number in enumerate(data_numbers):
            monitor_data = get_plotting_data(data_number, normalize=False, fitit=False, return_monitor = True)
            for i, label in enumerate(monitor_data[0]):
                color = colors[j]
                marker = markers[i]
                ax[1].scatter(monitor_data[1][i], monitor_data[2][i], label=f"{data_number} - {label}", color=color, marker=marker)
                
    ax[0].set_xlabel("Optical detuning (MHz)")
    ax[0].set_ylabel("Transmission (V)")
    ax[0].legend()
    ax[0].text(0,1.02,data, transform = ax[0].transAxes)
    ax[1].set_xlabel("Optical detuning (MHz)")
    ax[1].set_ylabel("Monitor (V)")
    ax[1].legend()
    ax[1].text(0,1.02,data, transform = ax[1].transAxes)
    ax[0].grid()
    ax[1].grid()
    if note is not None:
        ax[0].text(0.1,0.1, note, transform = ax[0].transAxes)
    plt.tight_layout()
    plt.show()


def get_plotting_data(data_number, normalize=True, fitit=False, labels=None, return_monitor = False):
    # GET DATA
    data, headers = get_experiment_data(data_number)
    detunings_MHz = headers["detunings"].to("MHz").magnitude
    transmissions_avg, transmissions_err = group_and_average_data(data["transmissions_avg"], headers["params"]["detect"]["cycles"], return_err=True)
    monitors_avg, monitors_err = group_and_average_data(data["monitors_avg"], headers["params"]["detect"]["cycles"], return_err=True)

    # ARRAYS TO RETURN
    labels_new = []
    xs = []
    ys = []
    ys_err = []
    xfits = []
    yfits = []
    
    # LOOP THROUGH ALL LABELS (SET BY ["detect"]["cycles"][LABEL] IN THE params DICT)
    for i, ((label, transmission), (_, transmission_err), (_, monitor), (_, monitor_err)) in enumerate(
        zip(transmissions_avg.items(), 
            transmissions_err.items(), 
            monitors_avg.items(),
            monitors_err.items(),
           )
        ):
        
        # IF LABELS NOT SPECIFICIED: RETURN ALL LABELS. 
        # ELSE ONLY PLOT SPECIFIED LABELS
        if labels is None:
            pass
        else:
            if label not in labels:
                continue

        # NORMALIZE WITH MONITORS PD
        if normalize:
            y_err = (transmission/monitor)*np.sqrt((transmission_err/transmission)**2 + (monitor_err/monitor)**2)
            y = transmission / monitor
        elif return_monitor:
            y_err = monitor_err
            y = monitor
        else:
            y_err = transmission_err
            y = transmission
            
        # TODO: UPDATE MASK SETTINGS FOR E>0, E<0
        mask = detunings_MHz < 1e13

        labels_new.append(label)
        xs.append(detunings_MHz[mask])
        ys.append(y)
        ys_err.append(y_err)

        # FITTER
        if fitit:
            xfit = np.linspace(min(detunings_MHz[mask]), max(detunings_MHz[mask]), 1000)
            fitter = get_gaussian_fit(detunings_MHz[mask], y[mask], p0 = {"sigma": 0.5, "a": -0.1, "b": -0.00001, "c": np.max(transmission[mask])})
            xfits.append(xfit)
            yfits.append(fitter.fitted_value(xfit))

    # RETURN WITH OR WITHOUT FITS
    if fitit:
        return (labels_new, xs, ys, ys_err, xfits, yfits)
    else:
        return (labels_new, xs, ys, ys_err)
    
def plot_antihole_data(data, normalize=True, fitit=False, errors=False, labels=None, return_monitor = False, divide_first_two=False):
    """
    input data: integer data number, or tuple data numbers for range, or list of data numbers
    """
    if isinstance(data, int):
        data_numbers = [data]
    elif isinstance(data, tuple):
        data_numbers = range(data[0], data[1]+1)
    elif isinstance(data, list):
        data_numbers = data
    
    colors = [f"C{i}" for i in range(10)]
    markers = [".","x","+","s""v","^","<",">",",","1","2","3","4","8","p","P","h","H"]
    fig, ax = plt.subplots()
    for j, data_number in enumerate(data_numbers):
        plotting_data = get_plotting_data(data_number, normalize=normalize, fitit=fitit, labels=labels, return_monitor = return_monitor)
        
        for i, label in enumerate(plotting_data[0]):
            color = colors[j]
            marker = markers[i]
            if errors:
                ax.errorbar(plotting_data[1][i], plotting_data[2][i], plotting_data[3][i], ls="", marker=marker, label=f"{data_number} - {label}", color=color)
            else:
                ax.scatter(plotting_data[1][i], plotting_data[2][i], marker=marker, label=f"{data_number} - {label}", color=color)
            if fitit:
                ax.plot(plotting_data[4][i], plotting_data[5][i], label=f"{data_number} - {label} fit", color=color)

    if divide_first_two:
        ax.scatter(plotting_data[1][0], plotting_data[2][0]/plotting_data[2][1], marker="o", label=f"div", color='k')
    
    ax.set_xlabel("Optical detuning (MHz)")
    if normalize:
        ax.set_ylabel("Normalized transmission (V/V)")
    else:
        if return_monitor is False:
            ax.set_ylabel("Transmission (V)")
        else:
            ax.set_ylabel("Monitor (V)")
    plt.legend()
    plt.grid()
    plt.tight_layout()
    plt.show()

# def print_data_number(data_number):
#     """
#     easier to read headers dictionary with this
#     """
#     _, headers = get_experiment_data(data_number)
#     pp = pprint.PrettyPrinter(depth=4)
#     pp.pprint(headers)

def _print_dict(d, indent_level=0):
    """
    Prints dictionaries in an easy to read format.
    """
    if not isinstance(d, dict):
        return
    
    indent = '    ' * indent_level 
    for key, value in d.items():
        #print(f"{indent}{key}: ")
        if not isinstance(d[key], dict):
            print(f"{indent}{key}: {d[key]}")
        else:
            print(f"{indent}{key}: ")
        _print_dict(value, indent_level + 1)

def print_data_number(data_number):
    """
    Prints headers for an experiment. 
    """
    d, h = get_experiment_data(data_number)
    _print_dict(h)

def _flatten_dict(d, flattened_dict, current_path=[]):
    """
    Iterates through a dictionary of dictionaries and puts everythign into one dictionary.
    For example, if params["detect"]["transition"] = "ac" this function will enter "detect transition" into the flattened_dict.
    """
    if not isinstance(d, dict):
        name = " ".join(current_path)
        flattened_dict[name] = d
        return
    
    for key, value in d.items():
        new_path = current_path + [key]
        _flatten_dict(value,flattened_dict, new_path)
        
def compare_experiments(data_number1, data_number2):
    """
    Prints parameters of two experiments which are different. 
    """
    _, headers1 = get_experiment_data(data_number1)
    _, headers2 = get_experiment_data(data_number2)
    flattened1 = {}
    _flatten_dict(headers1["params"], flattened1)
    flattened2 = {}
    _flatten_dict(headers2["params"], flattened2)
    
    for kk in flattened1:
        try:
            # if flattened1[kk] is a list of quantities:
            if all(isinstance(x, pint.Quantity) for x in flattened1[kk]) is True:
                # to check if a list of quantities are the same you must do this
                if str(flattened1[kk].magnitude) == str(flattened2[kk].magnitude):
                    continue
                else:
                    print(f"{kk}: {flattened1[kk]} \t {flattened2[kk]}")
            else:
                continue
        except:
            try:
                if flattened1[kk] == flattened2[kk]:
                    continue
                else:
                    print(f"{kk}: {flattened1[kk]} \t {flattened2[kk]}")
            except:
                 # if flattened1 has keys which flattened2 does not
                try:
                    print(f"{kk}: {flattened1[kk]} \t {flattened2[kk]}")
                except:
                    continue
                
    keys1 = set(flattened1.keys())
    keys2 = set(flattened2.keys())
    missing1 = keys1 - keys2 # keys in experiment 1 params but not experiment 2 params
    missing2 = keys2 - keys1

    if len(missing1) != 0:
        print(f"{data_number2} is missing:")
        for i in missing1:
            print("\t" + i)
            
    if len(missing2) != 0:
        print(f"{data_number1} is missing:")
        for i in missing2:
            print("\t" + i)