import numpy as np
import scipy.constants as c


S_Flambaum = 3.7
S_Sushkov = 0.1485
S_geo_mean = np.sqrt(S_Flambaum * S_Sushkov)

E_xtl = 3.1


def theta_from_W_T(W_T, S, E_xtl, A=0.33e-17):
    """Converts W_T to theta.

    Args:
        W_T: T-violating frequency shift in Hz.
        S: Schiff moment in theta * e * fm**3.
        E_xtl: Crystal electric field in GV / cm.
        A: Schiff moment conversion to atomic EDM in e * cm.
    """
    d_atom = A * S * c.e / 100
    I_dot_n = 0.75
    I = 2.5
    theta = np.abs(W_T * c.h * I / (d_atom * (E_xtl * 1e11)))
    return theta

