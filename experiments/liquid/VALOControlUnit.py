"""
Header file for SCPI commands over Ethernet to the Vexlum VALO Control Unit.
"""

import pyvisa
import time
import numpy as np

class VALOControlUnit:
    def __init__(self, ip_addr='192.168.0.113', port=55550, timeout=10000):
        self.ip_addr = ip_addr
        self.port = port
        self.timeout = timeout
        self.current_limit = 18 # A, until laser safety approval
        
        pyvisaaddr = '::'.join(['TCPIP0', self.ip_addr,
                                str(self.port), 'SOCKET'])
                                
        rm = pyvisa.ResourceManager()
        self.device = rm.open_resource(pyvisaaddr,
                                read_termination='\r\n',
                                write_termination='\n',
                                timeout=self.timeout)
               
        self._laser_temperature = self.laser_temperature
        self._laser_current = self.laser_current
        
        if "VX-Valo" not in self.get_name():
            raise ValueError("VALO Control Unit not loaded. Wrong address.")
        else:
            print("VALO Control Unit loaded.")

# ---- General Controls ---- #
    def close(self):
        self.device.close()
                                
    def get_name(self): #asking for identity
        return self.device.query('*IDN?')
        
    def reset(self): #resetting
        self.device.query('*RST') 
    
# ---- TEC Controls ---- #
    def get_TEC_temperature(self, driver_number : int, primary_sensor=True): #returns actual temperature from sensor in each driver
        '''
        driver_number:
            1: laser diode (LD_TEC)
            2: gain mirror (GAIN)
            3: SHG crystal (SHG)
            4: birefringent filter (BRF)
            5: etalon (ETALON)
            6: laser diode driver (LD)
        '''    
    
        sensor_number = 1 if primary_sensor else 2
        
        return float(self.device.query(f'MEAS{driver_number}:TEMP{sensor_number}?'))

    def get_TEC_temperature_setpoint(self, driver_number : int): #returns temperature setpoints
        return float(self.device.query(f'SOUR{driver_number}:TEMP:SPO?'))
        
    #sets temp setpoint
    def set_TEC_temperature_setpoint(self, driver_number : int, temp : float):
        self.device.write(f'SOUR{driver_number}:TEMP:SPO {temp}')
            
    
    def get_TEC_output(self, driver_number : int): #returns 1 if TEC is on and 0 if TEC is off
        return int(self.device.query(f'OUTP{driver_number}:STAT?'))
        

    def get_TEC_state(self, driver_number : int): #determines if the temperature controllers are on
        if self.get_TEC_output(driver_number) == 1:
            return True
        else:
            return False

    def TEC_on(self, driver_number : int, on): #turns the temperature controllers off and on
        if on is False:
            self.device.write(f'OUTP{driver_number}:STAT 0')
        elif on is True:
            self.device.write(f'OUTP{driver_number}:STAT 1')
            print('temperature controller', driver_number, 'is on')
        else:
            print('Input must be a boolean value')
            
   
# ---- laser Controls ---- #
    @property
    def laser_temperature(self): #returns temperature of the laser diode
        return float(self.get_TEC_temperature(1, 1))
    
    @property
    def laser_photodiode_current(self): #returns current of the photodiode in the laser, [mA]
        self.device.write(f'SOUR6:OPTI:CALA 0')
        self.device.write(f'SOUR6:OPTI:CALB 1')
        self.device.write(f'SOUR6:OPTI:CALC 0')
        return float(self.device.query(f'MEAS6:OPTI?'))
    
    @property
    def laser_current(self): #returns current of the laser diode driver, [A]
        return float(self.device.query(f'MEAS6:CURR?'))
    
    @property    
    def laser_current_setpoint(self): #returns current setpoint of laser
        return float(self.device.query(f'SOUR6:CURR:LIM?'))
        
    @property
    def laser_current_ramp_rate(self): #returns current ramp speed, [A/s]
        return float(self.device.query(f'SOUR6:CURR:RAMP?'))
        
    def _ramp_time(self, current): #returns the amount of time it takes to change the current, [s]
        return abs((current-self.laser_current)/self.laser_current_ramp_rate)    
        
    @laser_current_setpoint.setter #sets current setpoint
    def laser_current_setpoint(self, current : float):
        if current > self.current_limit:
            raise ValueError(f'Current above {self.current_limit} A limit.')
        else:
            self.device.write(f'SOUR6:CURR:LIM {current}')
            if self.laser_on == True: 
                time.sleep(self._ramp_time(current))
            

    @property
    def laser_on(self): #returns if the current to the laser is on
        if self.get_TEC_output(6) == 1:
            return True
        else:
            return False
    
    @laser_on.setter #turns the laser on and off
    def laser_on(self, on):
        cont = True
        if on is False:
            self.device.write('OUTP6:STAT 0')
            time.sleep(self._ramp_time(0))
        elif on is True:
            for driver_number in np.arange(1, 5, 1): #making sure all the temperature controllers are on
                if self.get_TEC_output(driver_number) == 0:
                    print ('Temperature controller', driver_number, 'is not on')
                    cont = False
                    break
            if cont is True:
                if not self.laser_on:
                    self.device.write('OUTP6:STAT 1')
                    time.sleep(self._ramp_time(self.laser_current_setpoint))
                    if self.laser_on:
                        print('laser is on')
        else:
            print('Input must be a boolean value')