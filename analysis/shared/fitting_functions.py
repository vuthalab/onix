from typing import Union, Iterable, Callable, Tuple, Annotated, Any, Dict, List
import numpy as np
from onix.analysis.fitter import Fitter

def get_fitter(xs: np.ndarray, ys: np.ndarray, function: Callable, 
               p0: Iterable = None, bounds: Iterable = None, 
               maxfev: int = 10000, set_absolute_sigma: bool = False):
    """
    Args:
        xs: np array for x
        ys: np array for y
        function: function to fit to
        p0: initial guess {"a": 1.1, "b": 2.2, ...}
        bounds: bounds on parameters {"a": [0, 1], "b": [-2, 2], ...}
        maxfev: maximum iterations for fitter
        set_absolute_sigma: 
    """
    fitter = Fitter(function)
    fitter.set_absolute_sigma(set_absolute_sigma)
    fitter.set_data(xs, ys)
    if p0 is not None:
        fitter.set_p0(p0)
    if bounds is not None:
        for bound_var, bound in bounds.items():
            fitter.set_bounds(bound_var, bound[0], bound[1])
    fitter.fit(maxfev=maxfev)
    return fitter

def linear(x: Union[float, np.ndarray], a: float, b: float):
    return x * a + b

def gaussian0(f: Union[float, np.ndarray], f0: float, a: float, sigma: float) -> Union[float, np.ndarray]:
    """
    Gaussian.
    """
    return a * np.exp(-(f - f0) ** 2 / (2 * sigma ** 2))

def gaussianC(f: Union[float, np.ndarray], f0: float, a: float, sigma: float, c: float) -> Union[float, np.ndarray]:
    """
    Gaussian with constant.
    """
    return a * np.exp(-(f - f0) ** 2 / (2 * sigma ** 2)) + c

def gaussianL(f: Union[float, np.ndarray], f0: float, a: float, sigma: float, b: float, c: float) -> Union[float, np.ndarray]:
    """
    Gaussian with line.
    """
    return gaussian0(f, f0, a, sigma, c) + b * f + c

def two_peak_gaussian(f: Union[float, np.ndarray], f1: float, f2: float, a1: float, a2: float,
                      sigma1: float, sigma2: float, b: float, c: float) -> Union[float, np.ndarray]:
    """
    Two Gaussians with linear background.
    """
    return gaussian0(f, f1, a1, sigma1) + gaussian0(f, f2, a2, sigma2) + c + b * f

def four_peak_gaussian(f: Union[float, np.ndarray], f1: float, f2: float, f3: float, f4: float, a1: float, a2: float, a3: float, a4: float,
                       sigma1: float, sigma2: float, sigma3: float, sigma4: float, c: float) -> Union[float, np.ndarray]:
    """
    Four Gaussians with linear background.
    """
    return gaussian0(f, f1, a1, sigma1) + gaussian0(f, f2, a2, sigma2) + gaussian0(f, f3, a3, sigma3) + gaussian0(f, f4, a4, sigma4) + c

def exp_decay(t: Union[float, np.ndarray], tau: float, a: float) -> Union[float, np.ndarray]:
    """
    Exponential decay.
    """
    return a * (np.exp(-t / tau) - 1)

def power_law(x: Union[float, np.ndarray], p: float, a: float) -> Union[float, np.ndarray]:
    """
    Power law with factor.
    """
    return a * x**p
