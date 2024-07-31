import numpy as np
import matplotlib.pyplot as plt
from schemdraw import logic
import schemdraw

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


def plot(seq: list[tuple], vis='schem', scale="int"):
       """

       :param seq: Sequence of lasers fired
       :param vis: Visualisation method ('schem' or 'matplot')
       :param scale: Size of events ('int', 'log', 'real')
       :return: Plot of the Pulse Sequence
       """
       plots = ['ac', 'rf', 'lf']  # , 'ef']
       names = ['580nm laser', 'RF', 'LF']  # , 'Electric Field']

       if vis == 'schem':
              tdig = {i:[[],[0], []] for i in plots}
              running_total = 0
              tags = []
              for evnt in seq:
                     # Time scale display
                     channel = 'ac' if evnt[0][:-2] in ['optical_', 'detect'] else evnt[0][:2]
                     if scale == 'real':
                            evtime = evnt[1]
                     elif scale == "int":
                            evtime = 1
                     elif scale == "log":
                            evtime = np.log(evnt[1])/5 + 0.5

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
                     tags.append(f'[{ind}:{running_total}]+[{ind}:{running_total + evtime}] {evnt[1]}')
                     running_total += evtime

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
                     {'signal': [{'name': f'{i}', 'wave': tdig[i][0], 'async': tdig[i][1]}
                                  for i in tdig],
                     'edge': tags,
                     },
                     ygap=.5, grid=False)

       # Perhaps this works, but was not developed past POC, so wouldn't use
       if vis == 'matplot':
              figure, axis = plt.subplots(4, 1)
              if scale == "real":
                     s_times = sum([i[1] for i in seq])
              elif scale == "int":
                     s_times = len(seq)
              elif scale == "log":
                     s_times = sum([1 + np.log(i[1])/5 for i in seq])
              xaxis = np.arange(0, s_times+1, 1)
              graphs = {i:np.zeros(1) for i in plots}
              for evnt in seq:
                     channel = "ac" if evnt[0][:-2] in ['optical_', 'detect'] else evnt[0][:2]
                     if scale == "real":
                            evtime = evnt[1]
                     elif scale == "int":
                            evtime = 1
                     elif scale == "log":
                            evtime = np.log(evnt[1])
                     for fig in plots:
                            if fig == channel:
                                   graphs[fig] = np.hstack([graphs[fig], np.ones(evtime)])
                            else:
                                   graphs[fig] = np.hstack([graphs[fig], np.zeros(evtime)])
              for i in range(3):
                     axis[i].plot(xaxis, graphs[plots[i]])
                     axis[i].set_title(names[i])
              plt.show()


if __name__ == "__main__":
       inp = [('optical_ac', 25), ('rf_abar_bbar', 1), ('lf_8', 1), ('rf_abar_bbar', 1), ('detect_3', 256),
              # ('break', 10),
              ('optical_cb', 25), ('optical_ac', 25), ('rf_a_b', 1), ('lf_8', 1), ('rf_a_b', 1), ('detect_6', 256),
              ('optical_cb', 25)]

       plot(inp, scale="int")
