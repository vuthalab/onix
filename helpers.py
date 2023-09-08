import contextlib
import fractions as _frac
import io
import sys

import numpy as _np


def console_bold(text: str) -> str:
    """Returns bolded text for console use.

    Useful in IPython / Jupyter.
    """
    return f"\u001b[1m{text}\u001b[0m"


def present_float(value, error, digits=None, unit=""):
    """Presents a float value with error with proper significant digits.

    Example:
        present_float(1.0, 0.036, units="MHz")  # returns "1.00(4) MHz"
        present_float(1.0, 0.018)  # returns "1.000(18)"
        present_float(1.0, 0.1, digits=1)  # returns "1.0(1)"

    Args:
        value: float, numerical value.
        error: float, uncertainty associated with the value.
        digits: int or None, number of digits in error. Default None,
            which uses 1 digit if the first digit of error is greater or equal to 2,
            and uses 2 digits otherwise.
        unit: str, unit of the number. Default "".

    Returns:
        str, representation of the float value with error.
    """
    fp = _FormatParameter(value, error)
    if unit == "":
        unit_str = ""
    else:
        unit_str = f" {unit}"
    return fp.float_representation(digits) + unit_str


def data_identifier(data_numbers, data_name=""):
    """Returns a data identifier string for given data numbers.

    Example:
        data_identifier([1, 2, 3])  # returns "#1-3"
        data_identifier([1, 2, 3], "PMT")  # returns "PMT #1-3"
        data_identifier([1, 2, 3, 5, 6], "PMT")  # returns "PMT #1-3, 5-6"
        data_identifier([1, 2, 3, 5, 6, 8])  # returns "#1-3, 5-6, 8"
        data_identifier([8, 1, 5, 3, 2, 6])  # returns "#1-3, 5-6, 8"

    Args:
        data_numbers: list of int, data numbers.
        data_name: str, name of the data. Default "".
    """

    def data_numbers_to_str(data_numbers):
        if len(data_numbers) == 0:
            return ""
        last_datanum = data_numbers[0]
        start_datanum = data_numbers[0]
        datanum_str = "#"
        for kk in data_numbers[1:]:
            if kk - 1 != last_datanum:
                if last_datanum == start_datanum:
                    datanum_str += f"{last_datanum}, "
                else:
                    datanum_str += f"{start_datanum}-{last_datanum}, "
                start_datanum = kk
            last_datanum = kk
        if last_datanum == start_datanum:
            datanum_str += f"{last_datanum}; "
        else:
            datanum_str += f"{start_datanum}-{last_datanum}; "
        return datanum_str[:-2]  # removes the extra comma and space.

    data_numbers = sorted(data_numbers)
    if data_name != "":
        data_name = data_name + " "
    return data_name + data_numbers_to_str(data_numbers)


def sort_y_with_x(x, *args):
    """Sorts the y values with respect to the x values.

    Example:
        sort_y_with_x([1, 3, 2], [2, 3, 1])  # returns ([1, 2, 3], [2, 1, 3])
        sort_y_with_x([1, 3, 2], [3, 2, 1], [2, 1, 3])  # returns ([1, 2, 3], [3, 1, 2], [2, 3, 1])

    Args:
        x: list of sortable objects (e.g. floats, strs), x values.
        *args: list of objects, y values.

    Returns:
        (sorted_x, sorted_y_1, ..., sorted_y_n)
        sorted_x: sorted list of x.
        sorted_y_kk: list of lists of sorted y_kk values.
    """
    for y in args:
        if len(x) != len(y):
            raise ValueError("x and y must have the same length.")

    zipped = zip(x, *args)
    sorted_zipped = sorted(zipped)
    sorted_x = [kk[0] for kk in sorted_zipped]
    sorted_y = []
    for kk in range(len(args)):
        sorted_y.append([ll[kk + 1] for ll in sorted_zipped])
    return (sorted_x, *tuple(sorted_y))


@contextlib.contextmanager
def nostdout():
    """Hides the standard output from the decorated function."""
    save_stdout = sys.stdout
    try:
        sys.stdout = io.StringIO()
        yield
    finally:
        sys.stdout = save_stdout


class _FormatParameter:
    """Handles representation of a value with an uncertainty.

    This class should not be used directly outside of this module.
    Use `present_float` instead.
    """

    def __init__(self, value, error):
        self._value = value
        self._error = error

    def float_representation(self, num_of_error_digits=None):
        """Returns the float representation of parameter.

        Example:
            fp = FormatParameter(1.0, 0.96)
            fp.float_representation() # Returns "1.0(1.0)"
            fp.float_representation(2) # Returns "1.00(96)"

        Args:
            num_of_error_digits: (Optional) an int, number of significant digits in error.
                Default None, where 2 digits will be used if the rounded error starts with an 1,
                and 1 digit otherwise.

        Returns:
            A string, float representation of the parameter.
        """
        num_of_error_digits, is_rounded_up = self._get_default_error_digits(num_of_error_digits)
        round_digits = self._error_digits_to_round_digits(num_of_error_digits, is_rounded_up)
        value_rounded = self._value_float_str(round_digits)
        error_rounded = self._error_float_str(round_digits)
        return value_rounded + "(" + error_rounded + ")"

    def _get_default_error_digits(self, num_of_error_digits):
        if num_of_error_digits is None:
            num_of_error_digits = 1
            extra_error_digits, is_rounded_up = self._check_error_first_digit()
            num_of_error_digits += extra_error_digits
        else:
            is_rounded_up = False
        return (num_of_error_digits, is_rounded_up)

    def _check_error_first_digit(self):
        """Checks the first digit of the error.

        Determines whether the first error digit is 1 so an extra significant digit is needed.

        Returns:
            A 2-tuple (num_of_extra_error_digits, is_rounded_up).
            num_of_extra_error_digits is an int, 0 if the first error digit does not round
                to one, else 1.
            is_rounded_up is a bool, True if error rounding increases the number of error digits,
                else False.
        """
        error_digits = self._num_digits(self._error)
        scaled_error = _np.round(self._error * 10 ** (-error_digits + 1))
        if scaled_error >= 10 and scaled_error <= 19:
            return (1, False)
        elif scaled_error >= 95:
            scaled_error = _np.round(self._error * 10 ** (-error_digits))
            if scaled_error == 10:
                return (1, True)
        return (0, False)

    def _num_digits(self, number):
        return int(_np.floor(_np.log10(abs(number))))

    def _error_digits_to_round_digits(self, num_of_error_digits, is_rounded_up):
        """Gets the number of decimals that value and error should be rounded to.

        Returns:
            An int representing the number of decimals that value and error should be rounded to.
            Positive int represents number of decimals after the decimal point.
            Negative int represents number of decimals before the decimal point.
            0 represents rounding at the decimal point.
        """
        error_digits = self._num_digits(self._error)
        if is_rounded_up:
            return -error_digits + num_of_error_digits - 2
        else:
            return -error_digits + num_of_error_digits - 1

    def _value_float_str(self, round_digits):
        if round_digits <= 0:
            format_digits = 0
        else:
            format_digits = round_digits
        return "{0:.{1}f}".format(_np.round(self._value, round_digits), format_digits)

    def _error_float_str(self, round_digits):
        if round_digits <= 0:
            format_digits = 0
        else:
            format_digits = round_digits
        rounded_error = _np.round(self._error, round_digits)
        error_digits = self._num_digits(rounded_error)
        if error_digits < 0 and -error_digits <= round_digits:
            return "{0:.0f}".format(rounded_error * 10**round_digits)
        else:
            return "{0:.{1}f}".format(rounded_error, format_digits)

