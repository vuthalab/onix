from functools import wraps as _wraps
import numpy as _np
from scipy._lib._util import getfullargspec_no_self as _getfullargspec
from scipy.optimize import curve_fit as _curve_fit
from onix.helpers import present_float
from typing import Union, Iterable, Callable, Tuple, Annotated, Any, Dict, List

__all__ = ["Fitter"]


class Fitter:
    """Wraps scipy.optimize.curve_fit.

    Example:
        fitter = Fitter(fit_function)
        fitter.set_data(xdata, ydata, ydata_err)
        fitter.fit()
        print(fitter.all_results_str())
    """

    def __init__(self, fit_function, array_compatible=True):
        self._fit_kwargs = {"xdata": None, "ydata": None, "sigma": None}
        if array_compatible:
            self._fit_kwargs["f"] = fit_function
        else:
            self._fit_kwargs["f"] = self._wrap_array_noncompatible_function(fit_function)
        self.parameters = _getfullargspec(self._fit_kwargs["f"]).args[1:]

        self._fit_kwargs["absolute_sigma"] = True
        self._p0 = {}
        self._nicknames = {}
        self._units = {}
        self._lower_bounds = {}
        self._upper_bounds = {}
        for name in self.parameters:
            self._p0[name] = 1.0
            self._lower_bounds[name] = -_np.inf
            self._upper_bounds[name] = _np.inf
            self._nicknames[name] = name
            self._units[name] = ""
        self._update_p0_kwargs()
        self._update_bounds_kwargs()

        self._opt = None
        self._err = None

    def _wrap_array_noncompatible_function(self, fit_function):
        """Makes a function compatible with _np.ndarray arguments.

        Keeps the argument names and the docstring of fit_function.
        """

        def ndarray_decorator(f):
            @_wraps(f)
            def wrapper(*args, **kwds):
                if isinstance(args[0], _np.ndarray):
                    func = _np.vectorize(f)
                else:
                    func = f
                return func(*args, **kwds)

            return wrapper

        return ndarray_decorator(fit_function)

    @property
    def fit_function(self):
        """Fit function."""
        return self._fit_kwargs["f"]

    def set_data(self, xdata, ydata, sigma=None):
        """Sets fitting data.

        Args:
            xdata: array of floats, x-axis data. It can be a 2D array for multivariate fitting,
                and each element in x_data should be an array corresponding to one independent
                variable.
            ydata: array of floats, y-axis data.
            sigma: array of floats, y-axis data uncertainties. Default None. If None, weights
                on all data points are the same, and the reduced chi-square is set to 1 to estimate
                fitting errors.
        """
        self._fit_kwargs["xdata"] = _np.array(xdata)
        self._fit_kwargs["ydata"] = _np.array(ydata)
        if sigma is not None:
            self._fit_kwargs["sigma"] = _np.array(sigma)
        else:
            self._fit_kwargs["sigma"] = sigma

    def set_absolute_sigma(self, absolute_sigma):
        """Sets whether the uncertainties are absolute.

        If the uncertainties are absolute, the uncertainties are used to weight the fitting data
        and to calculate the fitting errors. If they are relative, the uncertainties are only used
        to weight the fitting data, and the fitting errors are estimated by setting the reduced
        chi-square to 1.

        The class sets uncertainties to be absolute by default.

        Args:
            absolute_sigma: bool, whether the uncertainties are absolute.
        """
        self._fit_kwargs["absolute_sigma"] = absolute_sigma

    def _update_p0_kwargs(self):
        p0 = []
        for name in self.parameters:
            p0.append(self._p0[name])
        self._fit_kwargs["p0"] = _np.array(p0)

    def set_p0(self, p0):
        """Sets fitting parameter default values.

        Args:
            p0: array of floats or dict, parameter default values.
                If an array of floats, it needs to be the same length as self.parameters.
                If a dict, the keys should be the parameter names and the values are floats.
        """
        if isinstance(p0, dict):
            for name in p0:
                if name not in self._p0:
                    raise ValueError(f"Parameter {name} is not defined.")
                self._p0[name] = p0[name]
        elif isinstance(p0, (list, _np.ndarray)):
            if isinstance(p0, _np.ndarray) and p0.ndim != 1:
                raise ValueError("Dimension of p0 must be 1.")
            if len(p0) != len(self.parameters):
                raise ValueError(f"p0 must have a length of {len(self.parameters)}.")
            for kk, value in enumerate(p0):
                self._p0[self.parameters[kk]] = value
        else:
            raise TypeError("p0 must be a dict, a list, or an array.")
        self._update_p0_kwargs()

    def _update_bounds_kwargs(self):
        lower_bounds = []
        upper_bounds = []
        for name in self.parameters:
            lower_bounds.append(self._lower_bounds[name])
            upper_bounds.append(self._upper_bounds[name])
        self._fit_kwargs["bounds"] = (_np.array(lower_bounds), _np.array(upper_bounds))

    def set_bounds(self, name, lower_bound=-_np.inf, upper_bound=_np.inf):
        """Sets fitting bounds of a parameter.

        Args:
            name: str, parameter name to set bounds.
            lower_bound: float, lower bound of the parameter.
            upper_bound: float, upper bound of the parameter.
        """
        if name in self.parameters:
            self._lower_bounds[name] = lower_bound
            self._upper_bounds[name] = upper_bound
        else:
            raise ValueError(f"Parameter {name} is not defined.")
        self._update_bounds_kwargs()

    def set_nicknames(self, nicknames: dict[str, str]):
        """Set nicknames for fit parameters."""
        for param_name in nicknames:
            if param_name not in self._nicknames:
                raise ValueError(f"Parameter {param_name} is not defined.")
            self._nicknames[param_name] = nicknames[param_name]

    def set_units(self, units: dict[str, str]):
        """Set units for fit parameters."""
        for param_name in units:
            if param_name not in self._units:
                raise ValueError(f"Parameter {param_name} is not defined.")
            self._units[param_name] = units[param_name]

    def fit(self, **kwargs):
        """Fits the data.

        Keyword arguments are passed to the scipy.optimize.curve_fit function.
        """
        try:
            fit_kwargs = self._fit_kwargs.copy()
            if fit_kwargs["sigma"] is None:
                fit_kwargs["absolute_sigma"] = False
            self._opt, cov = _curve_fit(**fit_kwargs, **kwargs)
            self._err = _np.sqrt(_np.diag(cov))
        except RuntimeError as e:
            self._opt = None
            self._err = None
            raise e

    def _param_list_to_dict(self, variable_list):
        result = {}
        for kk, param in enumerate(self.parameters):
            result[param] = variable_list[kk]
        return result

    @property
    def results(self):
        """Fitting results."""
        if self._opt is None:
            print("Fitting results are not generated")
            return self._param_list_to_dict([_np.nan for kk in self.parameters])
        return self._param_list_to_dict(self._opt)

    @property
    def errors(self):
        """Fitting errors."""
        if self._err is None:
            print("Fitting errors are not generated")
            return self._param_list_to_dict([_np.nan for kk in self.parameters])
        return self._param_list_to_dict(self._err)

    def fitted_value(self, x):
        """Returns fitted value.

        Args:
            x: float or array of floats, value(s) of independent variable(s) to evaluate the
                function at. May be a 2D float array for fitting a multivariate function, and
                each of the element should be a set of independent variable values to evaluate
                the function at.

        Returns:
            float or array of floats, evaluated value(s).
        """
        if self._opt is None:
            raise Exception("Fitting results are not generated")
        return self.fit_function(x, *self._opt)

    def guessed_value(self, x):
        """Returns guessed value from the default parameters.

        Args:
            x: float or array of floats, value(s) of independent variable(s) to evaluate the
                function at. May be a 2D float array for fitting a multivariate function, and
                each of the element should be a set of independent variable values to evaluate
                the function at.

        Returns:
            float or array of floats, evaluated value(s).
        """
        return self.fit_function(x, *self._fit_kwargs["p0"])

    def result_str(self, param_name, use_unit=True):
        """Returns a string that represents a fitted parameter value and error.

        Example:
            # fitter is a Fitter instance with fitter.fit() successfully run.
            # it has a fitted parameter "tau" of 0.312(10). The unit is second.
            >>> fitter.set_unit({"tau": "s"})
            >>> fitter.result_str("tau")
            "tau = 0.312(10) s"

        Args:
            param_name: str, name of the parameter.
            use_unit: bool, whether to include the unit.

        Returns:
            str, summary of fit result and error of the parameter.
        """
        result = self.results[param_name]
        error = self.errors[param_name]
        if "$" in self._nicknames[param_name]:
            output_str = self._nicknames[param_name][:-1] + " = " + present_float(result, error) + "$"
        else:
            output_str = self._nicknames[param_name] + " = " + present_float(result, error)
        if use_unit:
            output_str += " " + self._units[param_name]
        return output_str

    def all_results_str(self, use_unit=True):
        """Returns all fit results in a formatted string."""
        results_str = ""
        for _kk, name in enumerate(self.parameters):
            results_str += self.result_str(name, use_unit) + "\n"
        try:
            results_str += "Reduced $\\chi^2$ = {0:.2f}".format(self.reduced_chi)
        except Exception:
            results_str += "Reduced $\\chi^2$ is undefined."
        return results_str

    def residuals(self):
        """Returns an array of residuals, (ydata - model)."""
        if self._fit_kwargs["xdata"] is None or self._fit_kwargs["ydata"] is None:
            raise Exception("xdata and ydata are not defined.")
        residuals = self._fit_kwargs["ydata"] - self.fitted_value(self._fit_kwargs["xdata"])
        return residuals

    def studentized_residuals(self):
        """Returns an array of studentized residuals, (ydata - model) / error."""
        residuals = self.residuals()
        if self._fit_kwargs["sigma"] is None:
            raise Exception("sigma is not defined.")
        return residuals / self._fit_kwargs["sigma"]

    @property
    def reduced_chi(self):
        """Reduced chi-square for the fitting. Not defined if y-axis errors are not provided."""
        studentized_residuals = self.studentized_residuals()
        deg_of_freedom = len(self._fit_kwargs["xdata"]) - len(self.parameters)
        if deg_of_freedom == 0:
            raise Exception("Degree of freedom is 0. Cannot calculate reduced chi square.")
        return _np.sum(_np.power(studentized_residuals, 2)) / deg_of_freedom
    
def get_fitter(function: Callable, xs: _np.ndarray, ys: _np.ndarray, 
               errs: _np.ndarray = None, p0: Iterable = None, 
               bounds: Iterable = None, maxfev: int = 10000, set_absolute_sigma: bool = False):
    """
    Args:
        function: function to fit to
        xs: np array for x
        ys: np array for y
        errs: np array for errs
        p0: initial guess {"a": 1.1, "b": 2.2, ...}
        bounds: bounds on parameters {"a": [0, 1], "b": [-2, 2], ...}
        maxfev: maximum iterations for fitter
        set_absolute_sigma: 
    """
    fitter = Fitter(function)
    fitter.set_absolute_sigma(set_absolute_sigma)
    fitter.set_data(xs, ys, errs)
    if p0 is not None:
        fitter.set_p0(p0)
    if bounds is not None:
        for bound_var, bound in bounds.items():
            fitter.set_bounds(bound_var, bound[0], bound[1])
    fitter.fit(maxfev=maxfev)
    return fitter

def linear(x: Union[float, _np.ndarray], a: float, b: float):
    return x * a + b

def gaussian0(f: Union[float, _np.ndarray], f0: float, a: float, sigma: float) -> Union[float, _np.ndarray]:
    """
    Gaussian.
    """
    return a * _np.exp(-(f - f0) ** 2 / (2 * sigma ** 2))

def gaussianC(f: Union[float, _np.ndarray], f0: float, a: float, sigma: float, c: float) -> Union[float, _np.ndarray]:
    """
    Gaussian with constant.
    """
    return a * _np.exp(-(f - f0) ** 2 / (2 * sigma ** 2)) + c

def gaussianL(f: Union[float, _np.ndarray], f0: float, a: float, sigma: float, b: float, c: float) -> Union[float, _np.ndarray]:
    """
    Gaussian with line.
    """
    return gaussian0(f, f0, a, sigma, c) + b * f + c

def two_peak_gaussian(f: Union[float, _np.ndarray], f1: float, f2: float, a1: float, a2: float,
                      sigma1: float, sigma2: float, b: float, c: float) -> Union[float, _np.ndarray]:
    """
    Two Gaussians with linear background.
    """
    return gaussian0(f, f1, a1, sigma1) + gaussian0(f, f2, a2, sigma2) + c + b * f

def four_peak_gaussian(f: Union[float, _np.ndarray], f1: float, f2: float, f3: float, f4: float, a1: float, a2: float, a3: float, a4: float,
                       sigma1: float, sigma2: float, sigma3: float, sigma4: float, c: float) -> Union[float, _np.ndarray]:
    """
    Four Gaussians with linear background.
    """
    return gaussian0(f, f1, a1, sigma1) + gaussian0(f, f2, a2, sigma2) + gaussian0(f, f3, a3, sigma3) + gaussian0(f, f4, a4, sigma4) + c

def exp_decay(t: Union[float, _np.ndarray], tau: float, a: float) -> Union[float, _np.ndarray]:
    """
    Exponential decay.
    """
    return a * (_np.exp(-t / tau) - 1)

def power_law(x: Union[float, _np.ndarray], p: float, a: float) -> Union[float, _np.ndarray]:
    """
    Power law with factor.
    """
    return a * x**p

def cosx(x: Union[float, _np.ndarray], a: float, x0: float, b: float, c: float) -> Union[float, _np.ndarray]:
    """
    Power law with factor.
    """
    return a * _np.cos(x - x0) + b * x + c