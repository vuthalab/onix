import time
from datetime import datetime

from onix.data_tools import save_persistent_data
from onix.headers.pulse_tube import PulseTube

pt = PulseTube()

## functions
save_interval_seconds = 60

times = []
compresser_states = []
T_coolant_in = []
T_coolant_out = []
T_oil = []
T_helium = []
P_low = []
P_high = []
I_motor = []
t_hours = []

def append_status():
    try:
        pt.status(silent=True)
        state = pt.is_on()
        compresser_states.append(state)
        for kk in pt.variables:
            if kk == "coolant in temp [C]":
                T_coolant_in.append(pt.variables[kk])
            elif kk == "coolant out temp [C]":
                T_coolant_out.append(pt.variables[kk])
            elif kk == "oil temp [C]":
                T_oil.append(pt.variables[kk])
            elif kk == "helium temp [C]":
                T_helium.append(pt.variables[kk])
            elif kk == "low pressure [psi]":
                P_low.append(pt.variables[kk])
            elif kk == "high pressure [psi]":
                P_high.append(pt.variables[kk])
            elif kk == "motor current [A]":
                I_motor.append(pt.variables[kk])
            elif kk == "hours":
                t_hours.append(pt.variables[kk])
        times.append(time.time())
        return True
    except Exception as e:
        print(e)
        return False

def save_data():
    data = {
        "times": times,
        "compresser_states": compresser_states,
        "T_coolant_in_C": T_coolant_in,
        "T_coolant_out_C": T_coolant_out,
        "T_oil_C": T_oil,
        "T_helium_C": T_helium,
        "P_low_psi": P_low,
        "P_high_psi": P_high,
        "I_motor_A": I_motor,
        "running_time_hours": t_hours,
    }
    name = "Pulse Tube"
    data_id = save_persistent_data(name, data)
    print(data_id)

def clear_variables():
    global times, compresser_states, T_coolant_in, T_coolant_out
    global T_oil, T_helium, P_low, P_high, I_motor, t_hours
    times = []
    compresser_states = []
    T_coolant_in = []
    T_coolant_out = []
    T_oil = []
    T_helium = []
    P_low = []
    P_high = []
    I_motor = []
    t_hours = []


## take data loop
date = datetime.now().date()
try:
    while True:
        if not append_status():
            save_data()
            print("Pulse tube status reading failed. Monitor stopped.")
            break
        new_date = datetime.now().date()
        if new_date != date:
            save_data()
            clear_variables()
            date = new_date
        time.sleep(save_interval_seconds)
except KeyboardInterrupt:
    save_data()
    pass
