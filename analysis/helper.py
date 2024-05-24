import numpy as np


def group_and_average_data(data, cycles, average: bool = True):
    total_cycles = sum(cycles.values())
    remainder_to_label = {}

    """
    for cycle_n in range(total_cycles):
        last_index_of_label = 0

        for label in cycles:

            if cycles[label] > 0:
                last_index_of_label += cycles[label]

                if cycle_n < last_index_of_label:
                    remainder_to_label[cycle_n] = label
                    break
    """

    # makes a dictionary - {cycle number: what was detected in the cycle}
    for label in cycles.keys():
        temp = np.arange(current_label_no, current_label_no+cycles[label])
        new_dict = dict(zip(temp, [label for _ in temp]))
        remainder_to_label.update(new_dict)
        current_label_no += cycles[label]

    data_averages = {}
    for label in cycles:
        if cycles[label] > 0:
            data_averages[label] = []

    # Not sure what the following for loop does
    for kk in range(len(data)):
        remainder = kk % total_cycles
        data_averages[remainder_to_label[remainder]].append(data[kk])

    # ah_parameters_from_data1() used the same code as this function
    # but without the averaging part, so the averaging was made optional.
    if average:
        for label in cycles:
            if cycles[label] > 0:
                data_averages[label] = np.average(data_averages[label], axis=0)

    return data_averages
