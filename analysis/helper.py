import numpy as np


def group_and_average_data(data, cycles):
    total_cycles = sum(cycles.values())
    remainder_to_label = {}
    for kk in range(total_cycles):
        last_index_of_label = 0
        for label in cycles:
            last_index_of_label += cycles[label]
            if kk < last_index_of_label:
                remainder_to_label[kk] = label
                break
    data_averages = {}
    for label in cycles:
        data_averages[label] = []
    for kk in range(len(data)):
        remainder = kk % total_cycles
        data_averages[remainder_to_label[remainder]].append(data[kk])
    for label in cycles:
        data_averages[label] = np.average(data_averages[label], axis=0)
    return data_averages

