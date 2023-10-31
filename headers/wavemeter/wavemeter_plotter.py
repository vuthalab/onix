import numpy as np
import matplotlib.pyplot as plt
import time
import zmq
import matplotlib.animation as animation
from matplotlib.ticker import ScalarFormatter
from matplotlib import rcParams
rcParams.update({'figure.autolayout':True})
from wavemeter import WM

class LivePlotter:
    def __init__(self):
        
        self.wm = WM()
        

        self.freqs = np.array([np.array([0]) for i in range(8)])
        self.times = np.array([time.time()])
    
        self.refresh_data()
        self.freqs = self.freqs[:,1:]
        self.times = self.times[1:]
    
    def get_freq(self,channel):
        freq = self.wm.read_frequency(channel)
        try:
            freq = float(freq)
        except:
            freq = 0.0
        return freq
    
    
    def refresh_data(self,L=100):
        new_freqs = np.array([[self.get_freq(i+1)] for i in range(8)])
            
        self.freqs= np.append(self.freqs,new_freqs,axis=1)
        self.times = np.append(self.times,time.time())
        
        
        if len(self.times)>L:
            self.times = self.times[1:]
            self.freqs = np.array([item[1:] for item in self.freqs])
        
            
    
    def create_animation(self,channels=[1,2,3,4,5,6,7,8],t_refresh=60):
        anim_interval = 0.2
        L = t_refresh/anim_interval 
        self.refresh_data(L)
        self.start_time = time.time()
        self.start_freqs = self.freqs[:,-1]
        
        self.text_template = 'Avg: %.3f GHz, RMS: %.3f MHz'

        self.fig = plt.figure(figsize=(10,2*len(channels)))
        
        self.axs = []
        self.lines = []
        self.txts = []
        c = 1
        for chan in channels:
            new_ax = self.fig.add_subplot(len(channels),1,c)
            self.axs.append(new_ax)
            self.lines.append(new_ax.plot([0],[0])[0])
            
            new_ax.set_ylabel('Channel %i (GHz)'%chan)
            new_ax.yaxis.get_major_formatter().set_useOffset(False)
            
            self.txts.append(new_ax.text(0.05,0.1,self.text_template%(0,0),transform=new_ax.transAxes))
            
            c+=1
        new_ax.set_xlabel("time(s)") #the last one

            
        
        self.lines = tuple(self.lines)
        
                
        ani = animation.FuncAnimation(self.fig,self.animate,fargs=(channels,L),interval=1e3*anim_interval,frames=50,blit=False)
        plt.tight_layout()
        plt.show()

    def avg_rms(self,channel):
        try:
            avg = np.mean(self.freqs[channel-1])
            rms = np.sqrt(np.mean(np.square(self.freqs[channel-1]-avg)))
        except Exception as e:
            print(e)
            avg,rms = 0.0,0.0
        return avg,rms
        
    def animate(self,i,channels,L):
        self.refresh_data(L)
        for i in range(len(channels)):
            chan_index= channels[i]-1
            #try:
                #new_freqs = [float(f)-float(self.start_freqs[chan_index]) for f in self.freqs[chan_index]]
            #    new_freqs = [float(f) for f in self.freqs[chan_index]]
            #except:
            #    new_freqs = self.freqs[chan_index]
            new_freqs = self.freqs[chan_index]
            avg,rms = self.avg_rms(channels[i])
            
            self.lines[i].set_data(self.times-self.start_time,new_freqs)
            self.axs[i].set_xlim(self.times[0]-self.start_time,self.times[-1]-self.start_time)
            self.axs[i].set_ylim(min(new_freqs),max(new_freqs))
            
            self.txts[i].set_text(self.text_template%(avg,1e3*rms))
        return self.lines,

if __name__=='__main__':
    pltr = LivePlotter()
    pltr.create_animation(channels=[5],t_refresh=30)