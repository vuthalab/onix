import serial
import time
import re
import numpy as np
import matplotlib.pyplot as plt


class Quarto:
    def __init__(self, location='/dev/ttyACM1'):
        self.address = location
        self.device = serial.Serial(self.address,
                                    baudrate=115200,
                                    timeout=0.2)

        self.sample_time = 2e-6

        self.device.reset_input_buffer()
        self.device.reset_output_buffer()
        out = "state\n"
        self.device.write(out.encode('utf-8'))
        time.sleep(0.1)
        response = self.device.readlines()

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

        return self.errdata

    def plot_errdata(self):
        self.get_errdata()
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

            V = V - np.average(V)

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

            return W_V, f

    def get_linewidth(self, discriminator_slope: float):
        self.get_errdata()
        if self.errdata != []:
            V = self.errdata
            t = np.arange(0,len(V))
            t = t*self.sample_time

            K = discriminator_slope

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

    def close(self):
        self.device.close()
