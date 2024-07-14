import numpy as np 
import matplotlib.pyplot as plt
from onix.headers.quarto_monitor import Quarto
import time
from onix.data_tools import save_persistent_data

q = Quarto()
data_time = q.data_time
adc_interval = q.adc_interval()
ch1 = []
ch2 = []
ch3 = []
ch4 = []
t = []

# # testing code
# try:
#     while True:
#         ch1_data, ch2_data, ch3_data, ch4_data = q.data()
#         ch1.extend(ch1_data)
#         ch2.extend(ch2_data)
#         ch3.extend(ch3_data)
#         ch4.extend(ch4_data)
#         print(len(ch1_data), len(ch2_data), len(ch3_data), len(ch4_data))

#         time.sleep(1)

# except KeyboardInterrupt:
#     t_axis = np.arange(0,len(ch4), 1) * q.adc_interval()
#     plt.plot(t_axis, ch1, label = "Ch1", alpha = 0.5)
#     plt.plot(t_axis, ch2, label = "Ch2", alpha = 0.5)
#     plt.plot(t_axis, ch3, label = "Ch3", alpha = 0.5)
#     plt.plot(t_axis, ch4, label = "Ch4", alpha = 0.5)
#     plt.xlabel("Time (s)")
#     plt.ylabel("Signal (V)")
#     plt.legend()
#     plt.show()



try:
    while True:
        get_data_time = time.time() 

        ch1_data, ch2_data, ch3_data, ch4_data = q.data()

        ch1.append(np.mean(ch1_data))
        ch2.append(np.mean(ch2_data))
        ch3.append(np.mean(ch3_data))
        ch4.append(np.mean(ch4_data))
        
        start_time = get_data_time - len(ch1) * adc_interval
        data_time = np.mean([start_time, get_data_time])
        t.append(data_time)

        time.sleep(1)

except KeyboardInterrupt:
    data = {
        "Ch1": np.array(ch1), # TODO: verify the axes labelled on the box are correct. Change these labels here from channel to which magnetic field component they represent
        "Ch2": np.array(ch2),
        "Ch3": np.array(ch3),
        "Ch4": np.array(ch4),
    }

    headers = {
        "Device": "Bartington Mag690-100",
    }

    save_persistent_data("Magnetometer", data, headers)


    # plt.scatter(t, ch1, label = "Ch1", alpha = 0.5)
    # plt.scatter(t, ch2, label = "Ch2", alpha = 0.5)
    # plt.scatter(t, ch3, label = "Ch3", alpha = 0.5)
    # plt.scatter(t, ch4, label = "Ch4", alpha = 0.5)
    # plt.xlabel("Time (s)")
    # plt.ylabel("Signal (V)")
    # plt.legend()
    # plt.show()
