import time
from datetime import datetime

from onix.data_tools import save_persistent_data
from onix.data_tools._data_handler import get_exist_persistent_path
from onix.headers.CTC100 import CTC100

c1 = CTC100("192.168.0.107", multiplexed=False)
c2 = CTC100("192.168.0.105", multiplexed=False)

"""
Saves a reading from the temperature controller every day at midnight. 
Left Temp Controller: 192.168.0.107
Right Temp Controller: 192.168.0.105
"""

## functions
save_interval_seconds = 60

times = []
t_45ksid = []
t_4kplatform = []
t_45kplate = []
t_4kplate = []
zirstdnu = []
topsrbout =[]

btmhs = []
rubylid = []
heatmirror =[]
out1r = []
smblkhtr = []
out2r = []

def append_status():
    try:
        t_45ksid.append(c1.read("45ksid"))
        t_4kplatform.append(c1.read("4kplatform"))
        t_45kplate.append(c1.read("45kplate"))
        t_4kplate.append(c1.read("4kplate"))
        zirstdnu.append(c1.read("zirstdnu"))
        topsrbout.append(c1.read("topsrbout"))
        btmhs.append(c2.read("btmhs"))
        rubylid.append(c2.read("rubylid"))
        heatmirror.append(c2.read("heatmirror"))
        out1r.append(c2.read("out1r"))
        smblkhtr.append(c2.read("smblkhtr"))
        out2r.append(c2.read("out2r"))
        times.append(time.time())
        return True
    except Exception as e:
        print(e)
        return False

def save_data():
    data = {
        "times": times,
        "T_45k_sid_in_K": t_45ksid,
        "T_4k_platform_in_K": t_4kplatform,
        "T_45k_plate_in_K": t_45kplate,
        "T_4k_plate_in_K": t_4kplate,
        "zir_st_dnu_in_W": zirstdnu,
        "top_srb_out_in_W": topsrbout,
        "T_btm_hs_in_K": btmhs,
        "T_ruby_lid_in_K": rubylid,
        "heat_mirror_in_W": heatmirror,
        "out_1_R_in_Ohm": out1r,
        "out_2_R_in_Ohm": out2r,
        "sm_blk_htr_in_W": smblkhtr
        
    }
    name = "Temperature Controller"
    data_id = save_persistent_data(name, data)
    print(data_id)

def clear_variables():
    global times, t_45ksid, t_4kplatform, t_45kplate, t_4kplate, zirstdnu, topsrbout
    global btmhs, rubylid, heatmirror, out1r, smblkhtr, out2r
    times = []
    t_45ksid = []
    t_4kplatform = []
    t_45kplate = []
    t_4kplate = []
    zirstdnu = []
    topsrbout =[]

    btmhs = []
    rubylid = []
    heatmirror =[]
    out1r = []
    smblkhtr = []
    out2r = []


## take data loop
date = datetime.now().date()
try:
    while True:
        if not append_status():
            save_data()
            print("Temperatuer Controller reading failed. Monitor stopped.")
            break
        new_date = datetime.now().date()
        if new_date != date:
            save_data()
            clear_variables()
            date = new_date
        time.sleep(save_interval_seconds)
except KeyboardInterrupt:
    save_data()
    print(get_exist_persistent_path(2, "Temperature Controller"))
    pass