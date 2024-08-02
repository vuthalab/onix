import numpy as np
import matplotlib.pyplot as plt
from schemdraw import logic
import schemdraw
from onix.data_tools import get_experiment_data
from onix.units import ureg 
from onix.sequences.sequence import AWGZero, TTLOff
from onix.awg_maps import get_channel_from_name, awg_channels, ttl_channels

# Turns input call into human Latex
def clean_txt(txt):
       if txt == "optical_ac":
              return r"$a - c$"
       if txt == 'optical_cb':
              return r"$c - b$"
       if txt in ["rf_abar_bbar", "rf_abarbbar"]:
              return r"$\bar{a} - \bar{b}$"
       if txt == "rf_a_b":
              return r"$a - b$"
       if txt[:6] == 'detect':
              return rf"$detect$"
       return txt


def plot(raw_data:int, scale:str ='int', detailed = False):
       """
       :param raw_data: Trial Number, or list of events
       :param seq: Sequence of lasers fired
       :param scale: Size of events ('int', 'log', 'real')
       :return: Plot of the Pulse Sequence
       """
       data, headers = get_experiment_data(2552361)
       seq = headers["sequence"]
       # ef = [[], [], []]
       tdig = {i:[[],[], []] for i in headers["sequence"]._segments["__start"]._awg_pulses}
       trig_dig = {i:[[],[], []] for i in headers["sequence"]._segments["__start"]._ttl_pulses}
       running_total = 0
       tags = []

       for evnt in seq._segment_steps:
              real_event = False
              # Time scale display
              cycle_len = seq._segments[evnt[0]].duration
              if scale == 'real':
                     evtime, tiny_step = evnt[1]*cycle_len, headers["params"]["field_plate"]["ramp_time"].to("ms")
              elif scale == "int":
                     evtime, tiny_step = 1.5, 1
              elif scale == "log":
                     evtime, tiny_step = np.log(evnt[1]*cycle_len) + 1, 1       
              # Add each event to respective channel
              for fig in tdig:
                     if type(seq._segments[evnt[0]]._awg_pulses[fig]) is not AWGZero:
                            tdig[fig][0].append('1')
                            tdig[fig][1].append(running_total)
                            name = clean_txt(evnt[0])
                            tdig[fig][2].append(((name,f"{round(evnt[1]*cycle_len, 2):~P}"), (running_total, running_total + evtime)))
                            real_event = True
                     elif tdig[fig][0] == [] or tdig[fig][0][-1] != '0':
                            tdig[fig][0].append('0')
                            tdig[fig][1].append(running_total)
              for fig in trig_dig:
                     if type(seq._segments[evnt[0]]._ttl_pulses[fig]) is not TTLOff:
                            # print(fig)
                            trig_dig[fig][0].append('1')
                            trig_dig[fig][1].append(running_total)
                            name = clean_txt(evnt[0])
                            # print(name)
                            trig_dig[fig][2].append(((name,f"{round(evnt[1]*cycle_len, 2):~P}"), (running_total, running_total + evtime)))
                            real_event = True
                     elif trig_dig[fig][0] == [] or trig_dig[fig][0][-1] != '0':
                            trig_dig[fig][0].append('0')
                            trig_dig[fig][1].append(running_total)

              if not real_event and detailed:
                     tags.append(f'[{0}^:{running_total}][{0}:{running_total + evtime}] {clean_txt(evnt[0])}')
                     tags.append(f'[{0}:{running_total}]+[{0}:{running_total + evtime}] {round(evnt[1]*cycle_len, 2):#~P}')
              
              if real_event or detailed:
                     running_total += evtime
       
       # Final filtering
       dead_chnl = []
       i = 0
       for fig in tdig:
              tdig[fig][1].append(running_total)
              # From list to string (necesary to plot)
              tdig[fig][0] = ''.join(tdig[fig][0])
              # Find and remove dead channels
              if tdig[fig][2] == []:
                     dead_chnl.append(fig)
              else:
                     for name in tdig[fig][2]:
                            # print(name)
                            tags.append(f'[{i}^:{name[1][0]}][{i}^:{name[1][1]}] {name[0][0]}')
                            tags.append(f'[{i}:{name[1][0]}]+[{i}:{name[1][1]}] {name[0][1]}')
                     i += 1
       for chnl in dead_chnl:
              tdig.pop(chnl)
       dead_chnl = []
       for fig in trig_dig:
              trig_dig[fig][1].append(running_total)
              # From list to string (necesary to plot)
              trig_dig[fig][0] = ''.join(trig_dig[fig][0])
              # Find and remove dead channels
              if trig_dig[fig][2] == []:
                     dead_chnl.append(fig)
              else:
                     for name in trig_dig[fig][2]:
                            # print(name)
                            tags.append(f'[{i}^:{name[1][0]}][{i}^:{name[1][1]}] {name[0][0]}')
                            tags.append(f'[{i}:{name[1][0]}]+[{i}:{name[1][1]}] {name[0][1]}')
                     i += 1
       for chnl in dead_chnl:
              trig_dig.pop(chnl)

       with schemdraw.Drawing():
              logic.TimingDiagram(
                     {'signal': [{'name': f'AWG:{awg_channels[i]['name']}', 'wave': tdig[i][0], 'async': tdig[i][1],}
                                   for i in tdig] + [{'name': f'TTL: {ttl_channels[i]['name']}', 'wave': trig_dig[i][0], 'async': trig_dig[i][1],}
                                   for i in trig_dig], 
                     'edge': tags,
                     },
                     ygap=.5, grid= False, risetime= 0)

if __name__ == "__main__":
       plot(2552361, scale="int")
