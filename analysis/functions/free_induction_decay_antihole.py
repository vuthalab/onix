import os
import numpy as np
import scipy.stats as st
from scipy.optimize import curve_fit
from scipy import signal
import matplotlib.pyplot as plt

from onix.data_tools import get_experiment_data, open_analysis_folder, get_analysis_file_path
from onix.analysis.fitter import Fitter
from onix.helpers import data_identifier, console_bold, present_float
from onix.units import Q_, ureg

from tqdm import tqdm

def butter_highpass(cutoff, fs, order=5):
    nyq = 0.5 * fs
    normal_cutoff = cutoff / nyq
    b, a = signal.butter(order, normal_cutoff, btype='high', analog=False)
    return b, a

def butter_highpass_filter(data, cutoff, fs, order=5):
    b, a = butter_highpass(cutoff, fs, order=order)
    y = signal.filtfilt(b, a, data)
    return y

def add_label(ax, x=0.02, y=1.1):
    ax.text(x, y, identifier, transform=ax.transAxes)

def plot_decay(start_data_number, end_data_number = None, delay = 7e-6, num_detects = 2):
    """
    Plot the transmission signal for detection 1 and detection 2 across all experiments between start_data_number and end_data_number inclusive. 
    All plots will start at pump time + wait time + delay
    """
    num_experiments = 1
    if end_data_number is not None:
        num_experiments = end_data_number - start_data_number + 1
    
    # going across a row the detect number will change, going down a column the data number will change
    fig, ax = plt.subplots(num_experiments, num_detects, figsize = (10, num_experiments*5))
    
    index = 0
    
    while index < num_experiments:
        # get the data and set the offset time after which we will look for the decay
        data, header = get_experiment_data(start_data_number+index)
        fid_params = header["params"]["detect"]["fid"]
        start_time = (fid_params["pump_time"] + fid_params["wait_time"]).to("s").magnitude + delay
        
        for kk in range(len(data["transmissions_avg"])):
            # convert index of data number to time, and consider only times after start_time
            times = np.arange(len(data["transmissions_avg"][kk])) / header["params"]["digitizer"]["sample_rate"]
            mask = times > start_time

            if kk < len(data["transmissions_avg"]) / 2:
                ax.flatten()[2*index].plot(times[mask] * 1e6, data["transmissions_avg"][kk][mask], alpha=0.5)
                ax.flatten()[2*index].set_title(f"{start_data_number+index} Detect 1")
                ax.flatten()[2*index].set_ylabel("Voltage (V)")

            else: 
                ax.flatten()[2*index+1].plot(times[mask] * 1e6, data["transmissions_avg"][kk][mask], alpha=0.5)
                ax.flatten()[2*index+1].set_title(f"{start_data_number+index} Detect 2")
                ax.flatten()[2*index+1].set_ylabel("Voltage (V)")
            
    
        index += 1
    
    # add the x axis label for the bottom left plot only
    ax.flatten()[-2].set_xlabel("time (us)")
    plt.tight_layout()
    plt.show()



def plot_spectrum(start_data_number, end_data_number = None, delay = 7e-6, num_detects = 2):
    """
    Plot the Fourier Transform of the detection signal for all experiments in between start_data_number and end_data_number, inclusive
    The subplot on the ith row and jth column will be the jth detection from the ith experiment
    Each subplot will have multiple traces corresponding to the multiple detects we do

    The data we take the Fourier Transform of is the data after pump time + probe time + delay
    """
    num_experiments = 1
    if end_data_number is not None:
        num_experiments = end_data_number - start_data_number + 1
    
    # going across a row the detect number will change, going down a column the data number will change
    fig, ax = plt.subplots(num_experiments, num_detects, figsize = (10, num_experiments*5))
    
    index = 0

    data, header = get_experiment_data(start_data_number+index)
    times = np.arange(len(data["transmissions_avg"][0])) / header["params"]["digitizer"]["sample_rate"]
    fid_params = header["params"]["detect"]["fid"]
    start_time = (fid_params["pump_time"] + fid_params["wait_time"]).to("s").magnitude + delay
    mask = times > start_time

    
    time_resolution = times[1] - times[0]
    duration = times[mask][-1] - times[mask][0]
    N = duration / time_resolution + 1
    fs = np.fft.rfftfreq(len(data["transmissions_avg"][00][mask]), d=time_resolution)[1:]
            
    ys_sum_detect1 = np.zeros(len(fs)) * 1j
    ys_sum_detect2 = np.zeros(len(fs)) * 1j
    while index < num_experiments:
        # get the data and set the offset time after which we will look for the decay
        data, header = get_experiment_data(start_data_number+index)
        fid_params = header["params"]["detect"]["fid"]
        start_time = (fid_params["pump_time"] + fid_params["wait_time"]).to("s").magnitude + delay
        
        for kk in range(len(data["transmissions_avg"])):
            # get the times and consider only the data from times > start_time
            times = np.arange(len(data["transmissions_avg"][kk])) / header["params"]["digitizer"]["sample_rate"]
            mask = times > start_time

            # take Fourier Transform 
            time_resolution = times[1] - times[0]
            duration = times[mask][-1] - times[mask][0]
            N = duration / time_resolution + 1
            ys = np.fft.rfft(data["transmissions_avg"][kk][mask])[1:] / N
            #print(len(ys))
            fs = np.fft.rfftfreq(len(data["transmissions_avg"][kk][mask]), d=time_resolution)[1:]
            

            if kk < len(data["transmissions_avg"]) / 2:
                #ys_sum_detect1 += ys
                ax.flatten()[2*index].plot(fs, np.abs(ys)**2, alpha=0.5)
                ax.flatten()[2*index].set_title(f"{start_data_number+index} Detect 1")
                ax.flatten()[2*index].set_ylabel("Voltage (V)")
                ax.flatten()[2*index].set_xlim(0, 20e6)

                
            else: 
                #ys_sum_detect2 += ys
                ax.flatten()[2*index+1].plot(fs, np.abs(ys)**2, alpha=0.5)
                ax.flatten()[2*index+1].set_title(f"{start_data_number+index} Detect 2")
                ax.flatten()[2*index+1].set_ylabel("Voltage (V)")
                ax.flatten()[2*index+1].set_xlim(0, 20e6)
        
        #ax.flatten()[2*index].plot(fs, np.abs(ys_sum_detect1)**2)
        #ax.flatten()[2*index].set_ylabel("Fourier Mod Squared $V^2 s^2$")
        #ax.flatten()[2*index + 1].plot(fs, np.abs(ys_sum_detect2)**2)
        #ax.flatten()[2*index + 1].set_ylabel("Fourier Mod Squared $V^2 s^2$")
            
    
        index += 1
        
    ax.flatten()[-2].set_xlabel("Frequency (MHz)")
    plt.tight_layout()
    plt.show()

def plot_spectrum_coherent(start_data_number, end_data_number = None, delay = 7e-6, num_detects = 2):
    """
    Plot the Fourier Transform of the detection signal for all experiments in between start_data_number and end_data_number, inclusive
    The subplot on the ith row and jth column will be the jth detection from the ith experiment
    Each subplot will have multiple traces corresponding to the multiple detects we do

    The data we take the Fourier Transform of is the data after pump time + probe time + delay
    """
    num_experiments = 1
    if end_data_number is not None:
        num_experiments = end_data_number - start_data_number + 1
    
    # going across a row the detect number will change, going down a column the data number will change
    fig, ax = plt.subplots(num_experiments, num_detects, figsize = (10, num_experiments*5))
    
    index = 0

    data, header = get_experiment_data(start_data_number+index)
    times = np.arange(len(data["transmissions_avg"][0])) / header["params"]["digitizer"]["sample_rate"]
    fid_params = header["params"]["detect"]["fid"]
    start_time = (fid_params["pump_time"] + fid_params["wait_time"]).to("s").magnitude + delay
    mask = times > start_time

    
    time_resolution = times[1] - times[0]
    duration = times[mask][-1] - times[mask][0]
    N = duration / time_resolution + 1
    fs = np.fft.rfftfreq(len(data["transmissions_avg"][00][mask]), d=time_resolution)[1:]
            
    ys_sum_detect1 = np.zeros(len(fs)) * 1j
    ys_sum_detect2 = np.zeros(len(fs)) * 1j
    while index < num_experiments:
        # get the data and set the offset time after which we will look for the decay
        data, header = get_experiment_data(start_data_number+index)
        fid_params = header["params"]["detect"]["fid"]
        start_time = (fid_params["pump_time"] + fid_params["wait_time"]).to("s").magnitude + delay
        
        for kk in range(len(data["transmissions_avg"])):
            # get the times and consider only the data from times > start_time
            times = np.arange(len(data["transmissions_avg"][kk])) / header["params"]["digitizer"]["sample_rate"]
            mask = times > start_time

            # take Fourier Transform 
            time_resolution = times[1] - times[0]
            duration = times[mask][-1] - times[mask][0]
            N = duration / time_resolution + 1
            ys = np.fft.rfft(data["transmissions_avg"][kk][mask])[1:] / N
            #print(len(ys))
            fs = np.fft.rfftfreq(len(data["transmissions_avg"][kk][mask]), d=time_resolution)[1:]
            

            if kk < len(data["transmissions_avg"]) / 2:
                ys_sum_detect1 += ys
                # ax.flatten()[2*index].plot(fs, np.abs(ys), alpha=0.5)
                # ax.flatten()[2*index].set_title(f"{start_data_number+index} Detect 1")
                # ax.flatten()[2*index].set_ylabel("Voltage (V)")
                # ax.flatten()[2*index].set_xlim(0, 20e6)

                
            else: 
                ys_sum_detect2 += ys
                # ax.flatten()[2*index+1].plot(fs, np.abs(ys), alpha=0.5)
                # ax.flatten()[2*index+1].set_title(f"{start_data_number+index} Detect 2")
                # ax.flatten()[2*index+1].set_ylabel("Voltage (V)")
                # ax.flatten()[2*index+1].set_xlim(0, 20e6)
        
        ax.flatten()[2*index].plot(fs, np.abs(ys_sum_detect1)**2)
        ax.flatten()[2*index].set_ylabel("Fourier Mod Squared $V^2 s^2$")
        ax.flatten()[2*index + 1].plot(fs, np.abs(ys_sum_detect2)**2)
        ax.flatten()[2*index + 1].set_ylabel("Fourier Mod Squared $V^2 s^2$")
            
    
        index += 1
        
    ax.flatten()[-2].set_xlabel("Frequency (MHz)")
    plt.tight_layout()
    plt.show()