import numpy as np
from uncertainties import ufloat, unumpy
from onix.data_tools import get_experiment_data
from onix.analysis.helper import group_and_average_data

"""
Shared analysis functions used for every experiment. 
"""

analysis_dnum = 613

def data_identification_to_list(data_identification):
    if isinstance(data_identification, tuple):
        return range(data_identification[0], data_identification[1] + 1)
    elif isinstance(data_identification, int):
        return [data_identification]
    else:
        # it should be a list
        return data_identification
    
def get_normalized_transmission(data_number, fft_end_time_s = None, fft_average_scan = None, fft_first_N = None):
    data, header = get_experiment_data(data_number)
    if "fid" in header["params"]["detect"] and header["params"]["detect"]["fid"]["use"]:
        if (fft_end_time_s is None) or (fft_average_scan is None):
            raise Exception("FID analysis parameters missing.") 
        sample_rate = header["params"]["digitizer"]["sample_rate"]
        fid_params = header["params"]["detect"]["fid"]
        start_time = (fid_params["pump_time"] + fid_params["wait_time"]).to("s").magnitude + 7e-6
        fft_end_time = start_time + fft_end_time_s
        times = np.arange(len(data["transmissions_avg"][0])) / sample_rate
        mask = (times > start_time) & (times < fft_end_time)
        time_resolution = times[1] - times[0]
        fs = np.fft.rfftfreq(len(data["transmissions_avg"][0][mask]), d=time_resolution)
        duration = times[mask][-1] - times[mask][0]
        N = duration / time_resolution
        freqs_to_probe = []
        center_detuning = (header["params"]["detect"]["fid"]["probe_detuning"] - header["params"]["detect"]["detunings"][0]).to("Hz").magnitude
        if header["params"]["field_plate"]["use"]:
            electric_field_shift = header["params"]["field_plate"]["stark_shift"].to("Hz").magnitude
            freqs_to_probe.append(center_detuning - electric_field_shift)
            freqs_to_probe.append(center_detuning + electric_field_shift)
        else:
            freqs_to_probe.append(center_detuning)
        freqs_to_probe = np.abs(freqs_to_probe)
        detunings_MHz = np.array(freqs_to_probe) * 1e-6
        indices_to_probe = []
        for freq in freqs_to_probe:
            closest_index = np.argmin(np.abs(fs - freq))
            indices_to_probe.append(closest_index)
        normalized_avg = [[] for kk in freqs_to_probe]
        for kk, d in enumerate(data["transmissions_avg"]):
            if kk >= fft_first_N:
                continue
            ys = np.fft.rfft(d[mask]) * 2 / N
            for ll, closest_index in enumerate(indices_to_probe):
                normalized_avg[ll].append(np.sum(np.abs(ys[closest_index - fft_average_scan: closest_index+fft_average_scan+1])))
        normalized_avg_avg = np.abs(np.average(normalized_avg, axis=1))
        # normalized_avg_std = np.std(np.abs(np.array(normalized_avg) - normalized_avg_avg), axis=1)
        # normalized_avg_std /= len(normalized_avg[0])
        normalized_avg = {"3": -unumpy.uarray(normalized_avg_avg, np.zeros(len(normalized_avg_avg))), "6": ufloat(0,0)}

    else:
        detunings_MHz = header["detunings"].to("MHz").magnitude
        if "save_avg" not in header["params"]["detect"] or not header["params"]["detect"]["save_avg"]:
            if "1" in header["params"]["detect"]["cycles"] and "2" in header["params"]["detect"]["cycles"] and header["params"]["detect"]["cycles"]["1"] != header["params"]["detect"]["cycles"]["2"]:
                del header["params"]["detect"]["cycles"]["1"]
            transmissions_avg, transmissions_err = group_and_average_data(data["transmissions_avg"], header["params"]["detect"]["cycles"], return_err=True)
            monitors_avg, monitors_err = group_and_average_data(data["monitors_avg"], header["params"]["detect"]["cycles"], return_err=True)
            normalized_avg = {}
            for kk in transmissions_avg:
                if transmissions_avg[kk].ndim >= 1:
                    normalized_avg[kk] = unumpy.uarray(
                        transmissions_avg[kk] / monitors_avg[kk],
                        np.sqrt(
                            (transmissions_err[kk] / monitors_avg[kk]) ** 2
                            + (transmissions_avg[kk] * monitors_err[kk] / monitors_avg[kk]) ** 2
                        )
                    )
                else:
                    normalized_avg[kk] = ufloat(
                        transmissions_avg[kk] / monitors_avg[kk],
                        np.sqrt(
                            (transmissions_err[kk] / monitors_avg[kk]) ** 2
                            + (transmissions_avg[kk] * monitors_err[kk] / monitors_avg[kk]) ** 2
                        )
                    )
        else:
            normalized_avg = {}
            for kk in data:
                if kk.startswith("normalized_avg_"):
                    normalized_avg[kk[15:]] = unumpy.uarray(data[f"normalized_avg_{kk[15:]}"], data[f"normalized_err_{kk[15:]}"])
    return detunings_MHz, normalized_avg, header
