import numbers
import numpy as np
import numpy.typing as npt
import warnings
from pint import UnitRegistry, UnitStrippedWarning
ureg = UnitRegistry()
Q_ = ureg.Quantity


def num_to_Q(
    value: npt.ArrayLike | list[Q_] | Q_, unit: Q_
) -> Q_:
    """Converts number(s) to quantity.

    Supports conversion of numbers, list of numbers, numpy arrays, and list of quantities.
    """
    if isinstance(value, numbers.Number):
        return value * unit
    elif isinstance(value, list):
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UnitStrippedWarning)
                return np.array(value) * unit  # list of numbers.
        except Exception as e:
            try:
                return Q_.from_list(value).to(unit)  # list of quantities
            except Exception as e:
                parsed_value = []  # mixed numbers and quantities
                for kk in value:
                    if isinstance(kk, numbers.Number):
                        parsed_value.append(kk)
                    elif isinstance(kk, Q_):
                        parsed_value.append(kk.to(unit).magnitude)
                    else:
                        raise TypeError(f"Value {kk} of type {type(kk)} is not supported in a list.")
                return np.array(parsed_value) * unit
    elif isinstance(value, np.ndarray):
        return np.array(value) * unit
    elif isinstance(value, Q_):
        return value.to(unit)
    else:
        raise TypeError(f"Value {value} of type {type(value)} is not supported.")
