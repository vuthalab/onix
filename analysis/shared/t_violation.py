import numpy as np
from uncertainties import ufloat

#TODO: include 2, 3, 4 peak analysis and fix E_a in 2 peak analysis
class TViolation():
    def __init__(
        self, 
        f_1_u,
        f_1_u_err,
        f_1_d,
        f_1_d_err,
        f_2_u,
        f_2_u_err,
        f_2_d,
        f_2_d_err
    ):
        self.f_1_u = ufloat(f_1_u, f_1_u_err)
        self.f_1_d = ufloat(f_1_d, f_1_d_err)
        self.f_2_u = ufloat(f_2_u, f_2_u_err)
        self.f_2_d = ufloat(f_2_d, f_2_d_err)

    @staticmethod
    def E_a(f_1, f_2):
        return (f_1 - f_2)/2
    
    @staticmethod
    def E_b(f_1, f_2):
        return (f_1 + f_2)/2
    
    @staticmethod
    def W(E_u, E_d):
        return (E_u - E_d)/2
    
    def get_W_T(self):
        E_a_u = self.E_a(self.f_1_u, self.f_2_u)
        E_a_d = self.E_a(self.f_1_d, self.f_2_d)
        
        E_b_u = self.E_b(self.f_1_u, self.f_2_u)
        E_b_d = self.E_b(self.f_1_d, self.f_2_d)
        
        W_a = self.W(E_a_u, E_a_d)
        W_b = self.W(E_b_u, E_b_d)

        W_T = W_a - W_b

        return W_T
