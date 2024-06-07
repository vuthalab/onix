import time

import numpy as np
from onix.sequences.rf_spectroscopy import RFSpectroscopy
from onix.units import ureg
from onix.experiments.shared import (
    m4i,
    dg,
    update_parameters_from_shared,
    setup_digitizer,
    run_sequence,
    save_data,
)
from tqdm import tqdm
from onix.headers.quarto_frequency_lock import Quarto as f_lock_Quarto


## function to run the experiment
def get_sequence(params):
    sequence = RFSpectroscopy(params)
    return sequence


## parameters
default_params = {
    "name": "RF Spectroscopy",
    "sequence_repeats_per_transfer": 1,
    "data_transfer_repeats": 1,
    "eos": {
        "ac": {
            "name": "eo_ac",
            "amplitude": 4500,  # 4500
            "offset": -300.0 * ureg.MHz,
        },
        "bb": {
            "name": "eo_bb",
            "amplitude": 1900,  # 1900
            "offset": -300 * ureg.MHz,
        },
        "ca": {
            "name": "eo_ca",
            "amplitude": 1400,  # 1400
            "offset": -300 * ureg.MHz,
        },
    },
    "rf": {
        "amplitude": 0,  # 4200
        "detuning": (65) * ureg.kHz,
        "duration": 0 * ureg.ms,
    },
    "chasm": {
        "transitions": ["bb"], #, "rf_both"
        "scan": 2.5 * ureg.MHz,
        "durations": 100 * ureg.us,
        "repeats": 2000,
        "detunings": 0 * ureg.MHz,
        "ao_amplitude": 2000,
    },
    "antihole": {
        "transitions": ["ac", "ca"], #, "rf_b" (for rf assist)
        "durations": [100 * ureg.us, 100 * ureg.us],
        "repeats": 2000,
        "ao_amplitude": 2000,
    },
    "detect": {
        "transition": "bb",
        "detunings": (np.linspace(-2.5, 2.5, 20)) * ureg.MHz, #np.array([-2, 0]) * ureg.MHz, #  # np.array([-2, 0]) * ureg.MHz,
        "on_time": 5 * ureg.us, #5
        "off_time": 1 * ureg.us,
        "cycles": {
            "chasm": 0,
            "antihole": 64,
            "rf": 64,
        },
        "delay": 10 * ureg.us,
        "ao_amplitude": 450,
    },
    "field_plate": {
        "amplitude": 3800,
        "stark_shift": 2.2 * ureg.MHz,
        "use": False,
    }
}
default_params = update_parameters_from_shared(default_params)

default_sequence = get_sequence(default_params)
default_sequence.setup_sequence()
setup_digitizer(
    default_sequence.analysis_parameters["digitizer_duration"],
    default_sequence.num_of_record_cycles(),
    default_params["sequence_repeats_per_transfer"],
    ch1_range=default_params["digitizer"]["ch1_range"],
    ch2_range=default_params["digitizer"]["ch2_range"],
)

## timeit

from onix.data_tools import get_experiment_data
from onix.analysis.fitter import Fitter
from onix.analysis.helper import group_and_average_data
import matplotlib.pyplot as plt

def antihole_data(data_number):
    data, headers = get_experiment_data(data_number)

    detunings_MHz = headers["detunings"].to("MHz").magnitude
    transmissions_avg = group_and_average_data(data["transmissions_avg"], headers["params"]["detect"]["cycles"])
    monitors_avg = group_and_average_data(data["monitors_avg"], headers["params"]["detect"]["cycles"])

    use_positive = None
    antihole_avg = transmissions_avg["antihole"] #/ monitors_avg["antihole"]

    if "chasm" in transmissions_avg:
        chasm_avg = transmissions_avg["chasm"]
        antihole_normalized = antihole_avg / chasm_avg
    else:
        chasm_avg = None
        antihole_normalized = antihole_avg

    if use_positive == True:
        mask = detunings_MHz > 0
    elif use_positive == False:
        mask = detunings_MHz < 0
    else:
        mask = detunings_MHz < 1e13

    return (detunings_MHz[mask], antihole_normalized[mask])

plt.ion()
fig = plt.figure()
ax = fig.add_subplot(111)
first_data = True
while True:
    # EXPERIMENT
    params = default_params.copy()
    sequence = get_sequence(params)
    data = run_sequence(sequence, params)
    data_id = save_data(sequence, params, *data)

    # PLOT
    x, y = antihole_data(data_id)
    if first_data == True:
        line1, = ax.plot(x, y, 'r.') # Returns a tuple of line objects, thus the comma
    line1.set_xdata(x)
    line1.set_ydata(y)
    fig.canvas.draw()
    ax.relim()
    ax.autoscale_view()
    fig.canvas.flush_events()
    first_data = False

    # WAIT
    time.sleep(2)
