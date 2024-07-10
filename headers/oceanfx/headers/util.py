from typing import Optional

import numpy as np
import matplotlib.pyplot as plt
#plt.rc('text', usetex=True)

from scipy.optimize import curve_fit
from scipy.odr import Model, ODR, RealData
from scipy.special import chdtrc as chisqcdf
import onix.headers.oceanfx.oceanfx as header_file
import os
import platform
from uncertainties import ufloat, correlated_values
from uncertainties import unumpy as unp

from colorama import Fore, Back, Style, init
init(strip=False)


nom = unp.nominal_values
std = unp.std_devs
uarray = unp.uarray

def calibration_filepath():
    header_path = os.path.dirname(header_file.__file__)
    if platform.system() == "Windows":
        calibration_folder_path = header_path + "\calibration"
    elif platform.system() == "Linux":
        calibration_folder_path = header_path + "/calibration"
    else:
        raise Exception("Platform type cannot be identified as either windows or linux")
    return calibration_filepath

def display_parameters(fit_params, parameters):
    if parameters is None: return

    for value, metadata in zip(fit_params, parameters.items()):
        tag, initial = metadata
        _, unit = initial
        print(f'{tag:9s}', '=', display(value), f'{Style.DIM}{unit}{Style.RESET_ALL}' if unit else '')
    print()


def display_statistics(dof, reduced_chisq):
    cdf = chisqcdf(dof, reduced_chisq * dof)

    dof_color = Fore.LIGHTGREEN_EX if dof > 0 else Fore.LIGHTRED_EX
    chisq_color = Fore.LIGHTGREEN_EX if 0.3 < reduced_chisq < 3 else Fore.LIGHTRED_EX
    cdf_color= Fore.LIGHTGREEN_EX if (cdf > 0.01 and cdf < 0.99) else Fore.LIGHTRED_EX
    print(f'chisq/dof = {chisq_color}{reduced_chisq:.3f}{Style.RESET_ALL}', end=' | ')
    print(f'CDF = {cdf_color}{100*cdf:5.2f} %{Style.RESET_ALL}', end=' | ')
    print(f'{dof_color}{dof}{Style.RESET_ALL} dof')

    return {
        'dof': dof,
        'chisq/dof': reduced_chisq,
        'cdf': cdf,
    }


def fit(model, x, y, p0, absolute_sigma=False):
    p0_arr = np.array([entry[0] for entry in p0.values()])
    meta = {tag: entry[1] for tag, entry in p0.items()}

    popt, pcov = curve_fit(
        model, nom(x), nom(y),
        p0=p0_arr,
        sigma=std(y), absolute_sigma=absolute_sigma
    )
    fit_params = correlated_values(popt, pcov, tags=p0.keys())

    pred = model(nom(x), *popt)
    residuals = y - pred
    dof = len(y) - len(fit_params)
    chisq = np.square(nom(residuals)/std(residuals)).sum()

    stats = display_statistics(dof, chisq/dof)
    display_parameters(fit_params, p0)

    return fit_params, (meta, stats), residuals


def odr_fit(model, x, y, p0):
    beta0 = [entry[0] for entry in p0.values()]
    meta = {tag: entry[1] for tag, entry in p0.items()}

    data = RealData(nom(x), nom(y), sx=std(x), sy=std(y))
    odr_model = Model(lambda B, x: model(x, *B))
    fit = ODR(data, odr_model, beta0=beta0).run()

    popt, pcov = fit.beta, fit.cov_beta
    fit_params = correlated_values(popt, pcov, tags=p0.keys())

    pred = model(nom(x), *popt)
    residuals = y - pred # TODO: Do residuals properly
    dof = len(y) - len(fit_params)

    stats = display_statistics(dof, fit.res_var)
    display_parameters(fit_params, p0)

    return fit_params, (meta, stats), residuals


def plot(
        x, y,
        model=None,
        params=None, meta=None,

        x_min=None, x_max=None,
        text_pos=(0.98, 'top'),
        clear=True,
        label='Data',

        continuous=False,
        ax = plt,
        color = None, # If true, plot data and model in same color, and omit statistics
        alpha = 1,
    ):
    if clear: plt.cla()

    if continuous:
        ax.plot(
            nom(x), nom(y),
            zorder=10,
            color=color,
            label=label,
            alpha=alpha,
        )
        ax.fill_between(
            nom(x),
            nom(y) - 2 * std(y),
            nom(y) + 2 * std(y),
            alpha=0.3*alpha,
            zorder=-10,
            color=color,
        )
    else:
        ax.errorbar(
            nom(x), nom(y),
            xerr=std(x), yerr=std(y),
            capsize=2, fmt='.',
            label=label,
            zorder=10,
            color=color,
        )

    xlim = (min(nom(x) - 2 * std(x)), max(nom(x) + 2 * std(x)))
    if x_min is not None: xlim = (x_min, xlim[1])
    if x_max is not None: xlim = (xlim[0], x_max)

    xs = np.linspace(*xlim, 100)

    if model is not None:
        plt.plot(
            xs, model(xs, *nom(params)),
            label='Fit' if color is None else None,
            color=color
        )
        plt.xlim(*xlim)


        if color is None:
            labels = []
            metadata, stats = meta
            for entry, value in zip(metadata.items(), params):
                tag, unit = entry
                unit = unit or ''
                labels.append(f'{tag} = {display(value, table=True)} {unit}')

            labels.append(f"{stats['dof']} DOF")
            labels.append(f"$\\chi^2_{{red}}$ = {stats['chisq/dof']:.3f}")
            labels.append(f"$\\chi^2$-CDF = {stats['cdf']*100:.2f}%")
            plt.text(
                0.02, text_pos[0], 
                '\n'.join(labels),
                transform=plt.gca().transAxes,
                horizontalalignment='left',
                verticalalignment=text_pos[1],
            )

    return xs


##### Formatting #####
def display(value: ufloat,
        digits: Optional[int] = None,
        table: bool = False) -> str:
    """Return formatted string for given value with uncertainty."""

    try:
        power = int(np.floor(np.log10(abs(value.n))))
        scientific = power > 3 or power < -2
        if scientific:
            value = value / pow(10, power)
    except:
        power = 3
        scientific = False

    if digits is None:
        try:
            digits = max(int(-np.floor(np.log10(value.s / 1.9))), 0) if value.s > 0 else 3
        except:
            digits = 10
    template_string = f'{{:.{digits}f}}'

    n_str = template_string.format(value.n)
    s_str = template_string.format(value.s)

    if table:
        value_str = f'{n_str} \\pm {s_str}'
        if scientific:
            value_str = f'$({value_str}) \\times 10^{{{power}}}$'
        else:
            value_str = f'${value_str}$'
    else:
        value_str = f'{n_str} \u00B1 {s_str}'
        if scientific:
            power_str = unicode_superscript(power)
            value_str = f'({value_str}) \u00D7 10{power_str}'
    return value_str

SUPERSCRIPT_CHARS = {
    '0': '\u2070', '1': '\u00B9', '2': '\u00B2', '3': '\u00B3', '4': '\u2074',
    '5': '\u2075', '6': '\u2076', '7': '\u2077', '8': '\u2078', '9': '\u2079',
    '+': '\u207A', '-': '\u207B'
}
def unicode_superscript(value: int):
    """Format given value as a superscript in Unicode."""
    return ''.join(SUPERSCRIPT_CHARS[i] for i in str(value))


##### Processing #####
def unweighted_mean(arr, samples_per_point: int = 1):
    arr = np.array(arr)
    mean = nom(arr)
    se = std(arr)
    N = len(arr)

    total_var = np.mean(np.square(se)) + np.square(np.std(mean)) / samples_per_point
    return ufloat(np.mean(mean), np.sqrt(total_var/N))


def weighted_mean(arr):
    arr = np.array(arr)
    x = nom(arr)
    s = std(arr)
    w = 1/(s*s)
    w /= w.sum()

    x_mean = (x*w).sum()
    s_mean = np.sqrt(np.square(s*w).sum())
    return ufloat(x_mean, s_mean)

def moving_average(arr, window_size):
    output = []
    for i in range(len(arr) - window_size + 1):
        output.append(unweighted_mean(arr[i:i+window_size]))
    return np.array(output)
