import traceback

from onix.headers.awg.m4i6622 import M4i6622
from onix.headers.digitizer.digitizer import Digitizer
from onix.headers.quarto_e_field import Quarto


try:
    m4i  # type: ignore
    print("m4i is already defined.")
except Exception:
    try:
        m4i = M4i6622()
    except Exception as e:
        m4i = None
        print("m4i is not defined with error:")
        print(traceback.format_exc())


try:
    dg  # type: ignore
    print("dg is already defined.")
except Exception:
    try:
        dg = Digitizer()
    except Exception as e:
        dg = None
        print("dg is not defined with error:")
        print(traceback.format_exc())


try:
    quarto_e_field  # type: ignore
    print("quarto_e_field is already defined.")
except Exception:
    try:
        quarto_e_field = Quarto()
    except Exception as e:
        quarto_e_field = None
        print("quarto_e_field is not defined with error:")
        print(traceback.format_exc())
