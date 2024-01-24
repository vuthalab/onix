import serial
import matplotlib.pyplot as plt
import numpy as np
import sys
import os
import time
import matplotlib.animation as animation
from scipy.optimize import minimize
import re

parent_folder = '/home/onix/gdrive/code/onix_control/'
os.chdir(parent_folder + '/headers/highfinesse_wavemeter_v4/')
from wavemeter import WM
wavemeter = WM()

class Quarto:
    def __init__(self, location='/dev/ttyACM2'):

        self.address = location

        self.device = serial.Serial(self.address,
                                    baudrate=115200,
                                    timeout=0.2)

        #self.device.open()

        self.sample_time = 2e-6

        self.device.reset_input_buffer()
        self.device.reset_output_buffer()
        out = "state\n"
        self.device.write(out.encode('utf-8'))
        time.sleep(0.1)
        response = self.device.readlines()

        self.state = self.getset_state()
        self.V_center = self.getset_V_center()
        self.V_scan = self.getset_V_scan()
        self.V_pushstep = self.getset_V_pushstep()
        self.V_output = self.get_V_output()

        self.PID_error = self.get_errdata()

    def getset_state(self, set=False, val=0):
        if set == False:
            self.device.reset_input_buffer()
            self.device.reset_output_buffer()
            out = "state\n"
            self.device.write(out.encode('utf-8'))
            time.sleep(0.1)
        else:
            self.device.reset_input_buffer()
            self.device.reset_output_buffer()
            out = "state " + str(val) + '\n'
            self.state = val
            self.device.write(out.encode('utf-8'))
            time.sleep(0.1)

        response = self.device.readlines()[0].decode('utf-8').strip('\n')
        response = int(re.findall(r'\d+', response)[0])

        self.state = response
        print("State is:", response)


    def getset_V_center(self, set=False, val=0):
        if set == False:
            self.device.reset_input_buffer()
            self.device.reset_output_buffer()
            out = 'vcenter\n'
            self.device.write(out.encode('utf-8'))
            time.sleep(0.1)
        else:
            self.device.reset_input_buffer()
            self.device.reset_output_buffer()
            out = "vcenter " + str(val) + '\n'
            self.V_center = val
            self.device.write(out.encode('utf-8'))
            time.sleep(0.1)

        response = self.device.readlines()[0].decode('utf-8').strip('\n')
        response = float(re.findall(r'\d+\.\d+', response)[0])

        self.V_center = response
        print("V center:", response)


    def getset_V_scan(self, set=False, val=0):
        if set == False:
            self.device.reset_input_buffer()
            self.device.reset_output_buffer()
            out = 'vscan\n'
            self.device.write(out.encode('utf-8'))
            time.sleep(0.1)
        else:
            self.device.reset_input_buffer()
            self.device.reset_output_buffer()
            out = "vscan " + str(val) + '\n'
            self.V_scan = val
            self.device.write(out.encode('utf-8'))
            time.sleep(0.1)

        response = self.device.readlines()[0].decode('utf-8').strip('\n')
        response = float(re.findall(r'\d+\.\d+', response)[0])

        self.V_scan = response
        print("V scan:", response)


    def getset_V_pushstep(self, set=False, val=0):
        if set == False:
            self.device.reset_input_buffer()
            self.device.reset_output_buffer()
            out = "vpushstep\n"
            self.device.write(out.encode('utf-8'))
            time.sleep(0.1)
        else:
            self.device.reset_input_buffer()
            self.device.reset_output_buffer()
            out = "vpushstep " + str(val) + "\n"
            self.V_pushstep = val
            self.device.write(out.encode('utf-8'))
            time.sleep(0.1)

        response = self.device.readlines()[0].decode('utf-8').strip('\n')
        response = float(re.findall(r'\d+\.\d+', response)[0])
        self.V_pushstep = response
        print("V push step:", response)



    def get_V_output(self):

        self.device.reset_input_buffer()
        self.device.reset_output_buffer()
        out = "voutput\n"
        self.device.write(out.encode('utf-8'))
        time.sleep(0.1)

        response = self.device.readlines()[0].decode('utf-8').strip('\n')
        response = float(re.findall(r'\d+\.\d+', response)[0])
        self.V_output = response
        print("V output:", response)


    def get_errdata(self):
        self.errdata = []
        self.device.reset_input_buffer()
        self.device.reset_output_buffer()
        out = "adc2data\n"
        self.device.write(out.encode('utf-8'))
        for i in range(50000):
            try:
                self.errdata.append(float(self.device.readline().strip()))
            except ValueError as e:
                print(i)
                raise e
        self.errdata = np.asarray(self.errdata)


    def plot_errdata(self):
        self.get_errdata()
        print(len(self.errdata))
        a = np.asarray(self.errdata)
        ts = np.arange(0,len(a))
        ts = ts*self.sample_time

        plt.plot(ts, a)
        plt.xlabel("time [s]")
        plt.ylabel("error voltage [V]")
        plt.show()

    def get_voltagespectrum(self):
        self.get_errdata()
        if self.errdata != []:
            V = self.errdata
            t = np.arange(0,len(V))
            t = t*self.sample_time

            #K = 100e-3/1e6

            V = V - np.average(V) #removing any offsets

            T = t[-1] - t[0]
            dt = t[1] - t[0]
            sample_time = 1/dt

            V_T = V/np.sqrt(T)
            V_f = np.fft.fft(V_T)*dt
            S_V = np.abs(V_f)**2
            f = np.fft.fftfreq(len(V_T),dt)


            W_V = 2*S_V[f>0]
            f = f[f>0]
            df = f[1]-f[0]

            #self.spectra.append(W_V)
            #self.f = f


            #plt.loglog(f, np.sqrt(W_V))
            #plt.ylabel("Voltage spectrum $\sqrt{W_V}$, [V/$\sqrt{\mathrm{Hz}}$]")
            #plt.xlabel("fourier frequency f, [Hz]")
            #plt.title("Voltage Spectra with laser (blue) blocked (orange)")
            #plt.show()

            return W_V, f

    def get_linewidth(self):
        self.get_errdata()
        if self.errdata != []:
            V = self.errdata
            t = np.arange(0,len(V))
            t = t*self.sample_time

            K = 100e-3/1e6

            V = V - np.average(V) #removing any offsets

            T = t[-1] - t[0]
            dt = t[1] - t[0]
            sample_time = 1/dt

            V_T = V/np.sqrt(T)
            V_f = np.fft.fft(V_T)*dt
            S_V = np.abs(V_f)**2
            f = np.fft.fftfreq(len(V_T),dt)

            W_V = 2*S_V[f>0]
            f = f[f>0]
            df = f[1]-f[0]

            W_nu = W_V/K**2
            W_phi = W_nu/f**2


            print("Sanity Check: Parseval's Theorem (these next two values should be equal)")
            V_rms_time = np.sqrt(np.trapz(V**2,x=t,dx=dt)/T)
            print("V_rms(t):", V_rms_time)

            V_rms_freq = np.sqrt(np.trapz(W_V, x=f, dx=df))
            print("V_rms(f):", V_rms_freq)

            varPhi = []
            for i in range(len(f)):
                varPhi.append(np.trapz(W_phi[i:], x=f[i:], dx=df))

            fig, axs = plt.subplots(3)

            axs[0].loglog(f, np.sqrt(W_V))
            axs[1].loglog(f, np.sqrt(W_phi))
            axs[2].loglog(f, varPhi)
            axs[2].loglog(f, 1/np.pi * np.ones_like(f), 'k--')

            fig.tight_layout(pad=1)

            axs[0].set(ylabel="Voltage spectrum $\sqrt{W_V}$, [V/$\sqrt{\mathrm{Hz}}$]")
            axs[1].set(ylabel="Phase spectrum $\sqrt{W_\phi}$, [rad/$\sqrt{\mathrm{Hz}}$]")
            axs[2].set(ylabel="Cumulative phase fluctuations $\int_f^\infty W_\phi(s)ds$, [Hz]")

            for ax in axs:
                ax.set(xlabel='fourier frequency f, [Hz]')
                ax.margins(0.01,0.1)

            varPhi = np.asarray(varPhi)
            idx = (np.abs(varPhi-1/np.pi)).argmin()
            print(f"Linewidth: {f[idx]} Hz")


            plt.show()
        else:
            print("No error data!")

    def get_errRMS(self):
        self.get_errdata()
        if self.errdata != []:
            V = self.errdata
            t = np.arange(0,len(V))
            t = t*self.sample_time

            V = V - np.average(V) #removing any offsets

            T = t[-1] - t[0]
            dt = t[1] - t[0]
            sample_time = 1/dt

            V_rms_time = np.sqrt(np.trapz(V**2,x=t,dx=dt)/T)
            print("V_rms:", V_rms_time)

            return V_rms_time
        else:
            print("No error data!")


    def animateerr(self, frame):
        t = np.arange(0,len(self.errdata))
        t = t*self.sample_time
        self.get_errdata()
        self.line.set_data(t, self.errdata)
        self.axe.set_ylim(min(self.errdata-0.001),max(self.errdata)+0.001)
        return self.errdata

    def animated_errdata(self):
        fig = plt.figure()

        self.get_errdata()
        t = np.arange(0,len(self.errdata))
        t = t*self.sample_time

        self.axe = plt.axes()
        #self.axe.set_ylim(-0.1,0.1)

        self.line, = self.axe.plot(t, self.errdata)
        plt.xlabel("time [s]")
        plt.ylabel("error voltage [V]")

        ani = animation.FuncAnimation(fig=fig, func=self.animateerr, frames = 10, interval=10, blit=False)
        plt.show()


    def close(self):
        self.device.close()

qu = Quarto("/dev/ttyACM1")
## plot avg spectra Vescent
spectra = []

for i in range(10):
    spec, f = qu.get_voltagespectrum()
    spectra.append(spec)
    time.sleep(5)


avg_spectra_blocked = np.mean(spectra, axis=0)

##
plt.loglog(f, np.sqrt(avg_spectra_blocked))
plt.ylabel("average voltage spectrum blocked$\sqrt{W_V}$, [V/$\sqrt{\mathrm{Hz}}$]")
plt.xlabel("fourier frequency f, [Hz]")
plt.title("Averaged voltage spectra blocked")
plt.show()



##
spectra = []

for i in range(10):
    spec, f = qu.get_voltagespectrum()
    spectra.append(spec)
    time.sleep(5)


avg_spectra_unblocked = np.mean(spectra, axis=0)

##
plt.loglog(f, np.sqrt(avg_spectra_unblocked))
plt.ylabel("average voltage spectrum blocked$\sqrt{W_V}$, [V/$\sqrt{\mathrm{Hz}}$]")
plt.xlabel("fourier frequency f, [Hz]")
plt.title("Averaged voltage spectra blocked")
plt.show()


##
plt.loglog(f, np.sqrt(avg_spectra_unblocked) - np.sqrt(avg_spectra_blocked))
plt.ylabel("average voltage spectrum unblocked - blocked$\sqrt{W_V}$, [V/$\sqrt{\mathrm{Hz}}$]")
plt.xlabel("fourier frequency f, [Hz]")
plt.title("Averaged voltage spectra unblocked - blocked (laser voltage spectra)")
plt.show()