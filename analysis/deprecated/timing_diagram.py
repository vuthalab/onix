import numpy as np
import matplotlib.pyplot as plt
from schemdraw import logic
import schemdraw
from onix.data_tools import get_experiment_data
from onix.units import ureg 

# Turns input call into human Latex
def clean_txt(txt):
       if txt == "optical_ac":
              return r"$a - c$"
       if txt == 'optical_cb':
              return r"$c - b$"
       if txt == "rf_abar_bbar":
              return r"$\bar{a} - \bar{b}$"
       if txt == "rf_a_b":
              return r"$a - b$"
       if txt[:6] == 'detect':
              if txt[7:15] == 'opposite':
                     return rf"$o-detect_{txt[16:]}$"
              return rf"$detect_{txt[7:]}$"
       return txt


# removes redundant 0s (eg: [0, 0, 1, 0, 0] -> [0, 1, 0])
def contrast(signal):
       c_sig = []
       for i in range(len(signal)-1):
              if signal[i:i+2] != ['0', '0']:  # signal[i+1] != signal[i]:
                     c_sig.append(signal[i])
       if c_sig == []:
              return []
       elif c_sig[-2:] != signal[-2:]:
              c_sig.append(signal[-1])
       return c_sig


def plot(raw_data:int|list, scale="int"):
       """
       :param raw_data: Trial Number, or list of events
       :param seq: Sequence of lasers fired
       :param scale: Size of events ('int', 'log', 'real')
       :return: Plot of the Pulse Sequence
       """
       if type(raw_data) is int:
              _, headers = get_experiment_data(raw_data)
              seq = headers["params"]["sequence"]["sequence"]
              efield = headers["params"]["field_plate"]["use"]
       else:
              seq = raw_data
              efield = False
       
       times = t_scale(headers['params'])
       t_dict = {"op":times[0], "de":times[1], "rf":times[2], "lf":times[3]}
       plots = ['op', 'rf', 'lf'] 
       ef = [[], [], []]

       tdig = {i:[[],[0], []] for i in plots}
       running_total = 0
       tags = []
       for evnt in seq:
              # Time scale display
              channel = evnt[0][:2] 
              #print(evnt)
              if channel in ['op', 'de', 'rf', 'lf']:
                     cycle_len = t_dict[channel]
                     if scale == 'real':
                            evtime, tiny_step = evnt[1]*cycle_len, headers["params"]["field_plate"]["ramp_time"].to("ms")
                     elif scale == "int":
                            evtime, tiny_step = 1.5, 1
                     elif scale == "log":
                            evtime, tiny_step = np.log(evnt[1]*cycle_len) + 1, 1       

                     if channel == "de":
                            channel = 'op'
                     
                     if efield:
                            ef_t = False
                            for etype in headers["params"]["field_plate"]["during"]:
                                   if etype[:2] == evnt[0][:2]:
                                          ef_t = headers["params"]["field_plate"]["during"][etype]
                            if ef_t and (ef[0] == [] or ef[0][-1] == '0'):
                                   ef[0].append('d1'), ef[1].extend([running_total, running_total + tiny_step]) 
                                   ef[2].extend([rf"$ramp up$", rf"$ef_on$"])
                                   tags.append(f'[3^:{running_total}][{3}:{running_total + tiny_step}] Ramp')
                                   tags.append(f'[3:{running_total}]+[{3}:{running_total + tiny_step}] \
                                          {round(headers["params"]["field_plate"]["ramp_time"].to("ms").magnitude, 2)}ms') 
                                   for i in tdig:
                                          # print(tdig[i][0])
                                          if tdig[i][0][-1] == '1':
                                                 # print("in")
                                                 tdig[i][0].append('0')
                                                 tdig[i][1].append(running_total)
                                   running_total += tiny_step
                                   tags.append(f'[{3}v:{running_total}][{3}:{running_total + evtime}] EF: {round(headers["params"]["field_plate"]["amplitude"]*2.5/2**15,2)}V')
                                   tags.append(f'[{3}:{running_total}]-[{3}:{running_total + evtime}] {round(evnt[1]*cycle_len, 2)}ms')
                            elif (not ef_t) and (ef[0] == [] or ef[0][-1] == 'd1'):
                                   ef[0].append('0'), ef[1].append(running_total)

                     # Add each event to respective channel
                     for fig in tdig:
                            if fig == channel:
                                   tdig[fig][0].append('1')
                            else:
                                   tdig[fig][0].append('0')
                            if tdig[fig][0][-2:] in (['0', '1'], ['1', '0'], ['1', '1'], '0', '1'):
                                   tdig[fig][1].append(running_total)

                     # Add graph labels
                     name = clean_txt(evnt[0])
                     try:
                            tdig[channel][2].append(name)
                            ind = plots.index(channel)
                     except KeyError:
                            ind = 0

                     tags.append(f'[{ind}^:{running_total}][{ind}^:{running_total + evtime}] {name}')
                     tags.append(f'[{ind}:{running_total}]+[{ind}:{running_total + evtime}] {round(evnt[1]*cycle_len, 2)}ms')
                     running_total += evtime
       tdig['ef'] = ef
       
       # Final filtering
       dead_chnl = []
       for fig in tdig:
              tdig[fig][1].append(running_total)
              # From list to string (necesary to plot)
              tdig[fig][0] = ''.join(contrast(tdig[fig][0]))
              # Find and remove dead channels
              if tdig[fig][2] == []:
                     dead_chnl.append(fig)
       for chnl in dead_chnl:
              tdig.pop(chnl)
       
       # Plot graph
       with schemdraw.Drawing():
              logic.TimingDiagram(
                     {'signal': [{'name': f'{i}', 'wave': tdig[i][0], 'async': tdig[i][1],}
                                   for i in tdig], 
                     'edge': tags,
                     },
                     ygap=.5, grid= False, risetime= 0)


def t_scale(params):
       optical = 1*ureg.ms
       detect = (params["detect"]["on_time"] + params["detect"]["off_time"] + params["detect"]["delay"])
       try:
           rf = 2*params["rf"]["T_0"] + params["rf"]["T_ch"]
       except:
           rf = 2*params["rf"]["HSH"]["T_0"] + params["rf"]["HSH"]["T_ch"]
       lf = params["lf"]["durations"][0] + params["lf"]["wait_times"][0]
       x = (t.to("ms").magnitude for t in [optical, detect, rf, lf])
       return (optical.to("ms").magnitude, detect.to("ms").magnitude, rf.to("ms").magnitude, lf.to("ms").magnitude)


if __name__ == "__main__":
       plot(2418714, scale="int")
