import numpy as np


def data_groups(data, headers):
    chasm_repeats = headers["params"]["detect"]["chasm_repeats"]
    antihole_repeats = headers["params"]["detect"]["antihole_repeats"]
    if "rf_repeats" in headers["params"]["detect"]:
        rf_repeats = headers["params"]["detect"]["rf_repeats"]
    else:
        rf_repeats = 0
    total_detect_repeats = chasm_repeats + antihole_repeats + rf_repeats
    experiment_repeats = headers["params"]["repeats"]

    chasm_avg = []
    antihole_avg = []
    rf_avg = []
    for kk in range(len(data["transmissions_avg"])):
        remainder = kk % total_detect_repeats
        if remainder < chasm_repeats:
            chasm_avg.append(data["transmissions_avg"][kk])
        elif remainder < chasm_repeats + antihole_repeats:
            antihole_avg.append(data["transmissions_avg"][kk])
        else:
            rf_avg.append(data["transmissions_avg"][kk])
    chasm_avg = np.array(chasm_avg)
    antihole_avg = np.array(antihole_avg)
    rf_avg = np.array(rf_avg)
    chasm_avg = np.average(chasm_avg, axis=0)
    antihole_avg = np.average(antihole_avg, axis=0)
    rf_avg = np.average(rf_avg, axis=0)

    if "monitors_avg" in data:
        monitor_chasm_avg = []
        monitor_antihole_avg = []
        monitor_rf_avg = []
        for kk in range(len(data["monitors_avg"])):
            remainder = kk % total_detect_repeats
            if remainder < chasm_repeats:
                monitor_chasm_avg.append(data["monitors_avg"][kk])
            elif remainder < chasm_repeats + antihole_repeats:
                monitor_antihole_avg.append(data["monitors_avg"][kk])
            else:
                monitor_rf_avg.append(data["monitors_avg"][kk])
        monitor_chasm_avg = np.array(monitor_chasm_avg)
        monitor_antihole_avg = np.array(monitor_antihole_avg)
        monitor_rf_avg = np.array(monitor_rf_avg)
        monitor_chasm_avg = np.average(monitor_chasm_avg, axis=0)
        monitor_antihole_avg = np.average(monitor_antihole_avg, axis=0)
        monitor_rf_avg = np.average(monitor_rf_avg, axis=0)
        return ((chasm_avg, antihole_avg, rf_avg), (monitor_chasm_avg, monitor_antihole_avg, monitor_rf_avg))
    
    return (chasm_avg, antihole_avg, rf_avg)

