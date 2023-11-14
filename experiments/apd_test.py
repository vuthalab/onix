import time

import numpy as np
from onix.data_tools import save_experiment_data
from onix.sequences.sequence import AWGSinePulse, AWGSineTrain, Segment, Sequence, TTLPulses
from onix.units import ureg, Q_

from onix.headers.pcie_digitizer.pcie_digitizer import Digitizer
from onix.headers.awg.M4i6622 import M4i6622

m4i = M4i6622()

## parameters

params = {
    "digitizer_channel": 0,
    "repeats": 3,

    "ao": {
        "channel": 0,
        "frequency": 80 * ureg.MHz,
    },

    "eo": {
        "channel": 1,
        "frequency": 200 * ureg.MHz,
    },

    "pump": {
        "duration": 1 * ureg.s,
        "ao_amplitude": 2400,
        "eo_amplitude": 3400,
    },

    "probe": {
        "duration": 1 * ureg.s,
        "ao_amplitude": 550,
        "eo_amplitude": 3400,
        "eo_modulation": True,
        "modulation_time": 5 * ureg.us,
    },
}

SEG_TIME = 5 * ureg.ms

sequence = Sequence()
pump = Segment("pump", SEG_TIME)
pump_repeats = int((params["pump"]["duration"] / SEG_TIME).to("").magnitude)
ao_pump = AWGSinePulse(params["ao"]["frequency"], params["pump"]["ao_amplitude"])
pump.add_awg_function(params["ao"]["channel"], ao_pump)
eo_pump = AWGSinePulse(params["eo"]["frequency"], params["pump"]["eo_amplitude"])
pump.add_awg_function(params["eo"]["channel"], eo_pump)
sequence.add_segment(pump)

probe = Segment("probe", SEG_TIME + 5 * ureg.us)
probe_repeats = int((params["probe"]["duration"] / SEG_TIME).to("").magnitude)
trigger = TTLPulses([[0, 5e-6]])
probe.add_ttl_function(params["digitizer_channel"], trigger)
ao_probe = AWGSinePulse(params["ao"]["frequency"], params["probe"]["ao_amplitude"])
probe.add_awg_function(params["ao"]["channel"], ao_probe)
if params["probe"]["eo_modulation"]:
    probe_inner_repeats = int((SEG_TIME / params["probe"]["modulation_time"]).to("").magnitude)
    amplitudes = [params["probe"]["eo_amplitude"] for kk in range(probe_inner_repeats)]
    frequencies = Q_.from_list([params["eo"]["frequency"] if kk % 2 == 0 else params["eo"]["frequency"] + 50 * ureg.MHz for kk in range(probe_inner_repeats)])
    eo_probe = AWGSineTrain(
        params["probe"]["modulation_time"],
        0 * ureg.s,
        frequencies,
        params["probe"]["eo_amplitude"],
    )
else:
    eo_probe = AWGSinePulse(params["eo"]["frequency"], params["probe"]["eo_amplitude"])
probe.add_awg_function(params["eo"]["channel"], eo_probe)
sequence.add_segment(probe)

sequence.setup_sequence(
    [
        ("pump", pump_repeats),
        ("probe", probe_repeats),
    ]
)

## setup the awg and digitizer
print("sequence setup started")
m4i.setup_sequence(sequence)
print("sequence setup finished")

## take data
sample_rate = int(1e8)
dg = Digitizer(False)
val = dg.configure_system(
    mode=2,
    sample_rate=sample_rate,
    segment_size=int(SEG_TIME.to("s").magnitude * sample_rate),
    segment_count=probe_repeats * params["repeats"],
    voltage_range=2000,
)
val = dg.configure_trigger(
    edge = 'rising',
    level = 30,
    source = -1,
    coupling = 1,
    range = 10000
)
acq_params = dg.get_acquisition_parameters()

transmissions = None
reflections = None
dg.arm_digitizer()
time.sleep(0.1)

for kk in range(params["repeats"]):
    print(f"{kk / params['repeats'] * 100:.0f}%")
    m4i.start_sequence()
    m4i.wait_for_sequence_complete()
m4i.stop_sequence()

digitizer_data = dg.get_data()
transmissions = np.array(digitizer_data[0])
reflections = np.array(digitizer_data[1])

photodiode_times = [kk / sample_rate for kk in range(len(transmissions[0]))]

n = sample_rate // int(1e6)
photodiode_times = np.mean(np.array(photodiode_times).reshape(-1, n), axis=1)
transmissions = np.mean(transmissions.reshape(params["repeats"] * probe_repeats, -1, n), axis=2)
reflections = np.mean(reflections.reshape(params["repeats"] * probe_repeats, -1, n), axis=2)

## save data
data = {
    "times": photodiode_times,
    "transmissions": transmissions,
    "monitors": reflections,
}
headers = {
    "params": params,
}
name = "APD Test"
data_id = save_experiment_data(name, data, headers)
print(data_id)

## empty
