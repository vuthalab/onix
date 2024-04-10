import numpy as np
from uncertainties import ufloat


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
        f_2_d_err,
        f_0 = 119.2e6,
        f_0_err = 0,
    ):
        self.f_1_u = ufloat(f_1_u, f_1_u_err)
        self.f_1_d = ufloat(f_1_d, f_1_d_err)
        self.f_2_u = ufloat(f_2_u, f_2_u_err)
        self.f_2_d = ufloat(f_2_d, f_2_d_err)
        self.f_0   = ufloat(f_0  , f_0_err)

    @staticmethod
    def E_a(f_1, f_2):
        return (f_1 - f_2)/2
    
    @staticmethod
    def E_b(f_1, f_2, f_0):
        return (f_1 + f_2)/2 - f_0
    
    @staticmethod
    def W(E_u, E_d):
        return (E_u - E_d)/2
    
    def get_W_T(self):
        E_a_u = self.E_a(self.f_1_u, self.f_2_u)
        E_a_d = self.E_a(self.f_1_d, self.f_2_d)
        
        E_b_u = self.E_b(self.f_1_u, self.f_2_u, self.f_0)
        E_b_d = self.E_b(self.f_1_d, self.f_2_d, self.f_0)
        
        W_a = self.W(E_a_u, E_a_d)
        W_b = self.W(E_b_u, E_b_d)

        W_T = W_a - W_b

        return W_T
    

test = TViolation(1, 0.1, 2, 0.1, 3, 0.1, 4, 0.1)

wt = test.get_W_T()

print(wt)