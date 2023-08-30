import numpy as np
import math
import random
from scipy import signal

SAMPLES  = 625000000

def gaussEnv(x):
    return signal.gausspulse(x)

def sin_for_time(freq1, freq2, time1,time2,x):


    samplePerNano = SAMPLES*10e-9

    x = x %((time1 + time2)*samplePerNano)

    index0 = 0
    for i in range(0,len(x)):
        if x[i] > time1*2.4:

            index0 = i
            break
    ret = np.zeros(x.size,dtype=int)


    ret[0:index0] = np.floor(2000*np.sin(np.multiply(2*math.pi*freq1/SAMPLES,x[0:index0])))
    ret[index0:] = np.floor(1000*np.sin(np.multiply(2*math.pi*freq2/SAMPLES,x[index0:])))
    return ret

def Batman(x):
    x = (x- 100000)/1000
    if abs(x) < 0.5:
        return math.floor(2.25*400*np.sin(x*300))
    elif abs(x) < 0.75:
        return math.floor(400*(3 * abs(x) + 0.75)*np.sin(x*300))
    elif abs(x) < 1:
        return math.floor(400*(9-8*abs(x))*math.sin(x*300))
    #elif abs(x) > 4 and abs(x) < 7:
    #    return math.floor(1000*(-3*math.sqrt(-(x/7)**2 + 1))*math.sin(x/10))
    elif abs(x) > 3 and abs(x) < 7:
        return math.floor(400*(3*math.pow(-(x/7)**2 + 1,0.5))*math.sin(x*300))
    elif abs(x) > 1 and abs(x) < 3:
        return math.floor(400* (1.5 - 0.5*abs(x) - 6 * math.sqrt(10)/14 *(math.sqrt(3-x**2 + 2 * abs(x)) -2))*math.sin(x*300))

    else:
        return 0

def sin(x,f=177000000, phi=0):
    return np.floor(3000*np.sin(np.multiply(2*math.pi*f/SAMPLES,x)+phi))

def envelope(x, tau):
    return (np.abs(x) < (tau/2)*SAMPLES)

def ramsey_sequence(x, tau, T, freq, phi_port, phi_ramsey):
    pulse1 = envelope(x-((tau/2)*SAMPLES), tau)*sin(x, f=freq, phi=phi_port)
    pulse2 = envelope(x-((tau + T + tau/2)*SAMPLES), tau)*sin(x, f=freq, phi=phi_port+phi_ramsey)

    return pulse1 + pulse2

def rabi_sequence(x, tau, freq, phi0):
    return envelope(x-((tau/2)*SAMPLES), tau)*sin(x, f=freq, phi=phi0)


def TL_signal(x, functionList, T_ramsey, T_rabi, channelNum):
    print(x[0])
    Y_temp = np.zeros((len(x)))
    for k in range(len(x)):
        if x[k] > 0 and x[k] < T_rabi*SAMPLES: #/channelNum:
            Y_temp[k] = Y_temp[k] + functionList[0](x[k])
        elif x[k] > T_ramsey*SAMPLES and x[k] < (T_ramsey+T_rabi)*SAMPLES: #/channelNum:
            Y_temp[k] = Y_temp[k] + functionList[1](x[k])
        else:
            Y_temp[k] = 0

    return Y_temp


def sin_over_range(x, start_freq, freq_range):
    number_of_100khz_steps = freq_range/1000 #100kHz
    x_length = len(x)
    number_of_x_per_100khz = x_length/number_of_100khz_steps
    return np.floor(6000*np.sin(np.multiply(2*np.pi*(start_freq + 1000*np.floor(np.multiply(x, 1/number_of_x_per_100khz)))/SAMPLES, x)))


def sin_over_range_random(x, start_freq, freq_range):
    number_of_100khz_steps = freq_range/100000 #100kHz
    x_length = len(x)
    number_of_x_per_100khz = x_length/number_of_100khz_steps
    return np.floor(2000*np.sin(np.multiply(2*np.pi*(start_freq + 100000*(np.mean(x)/number_of_x_per_100khz-np.floor(np.multiply(x, 1/number_of_x_per_100khz))))/SAMPLES, x)))

def sin_of_exp(x):
    x = 10*x
    return math.floor(1000 * math.sin(math.exp(x)))

def sin_of_ln(x):
    x = 10*x
    if x != 0:
        return math.floor(1000 * math.sin(math.log(x**2)))
    else:
        return 0

def weird_sin(x):
    a = 1000
    return math.floor(1000*np.where(x != a, math.floor((x-a)*math.sin(1/(x-a))), 0))

def gaussianEnvelope(x):
    x = x
    x0 = 10000
    sigma = 100000
    f = 2000000
    return math.floor(1000*np.exp(-np.power((x-x0),2) / sigma) * np.sin(np.multiply(x,2*math.pi*f/SAMPLES)))

def gaussianDist(x):
    x = x
    x0 = 1000
    sigma = 1000
    return np.floor(1000*np.exp(-(x-x0)**2 / sigma))

def firstOrderPolynomial(x):
    x = (x-1000)/100
    return np.floor(x)

def sechEnvelope(x):
    T= 1000
    f = 2000000
    x0 = 100000

    return math.floor(1000*(1/np.cosh((x-x0)/T)**2) * np.sin(x*2*math.pi*f/MEGA(200)))

def circle(x):
    x = x- 10000

    if np.abs(x) < 10000:
        return math.floor(x- 10000 * sqrt(10000**2 - x**2)*math.sin(x/3))
    else:
        return 0


