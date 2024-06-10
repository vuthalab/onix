from onix.headers.microphone import Quarto
from onix.headers.find_quarto import find_quarto
from pprint import pprint

q = Quarto()
ret = q.adc_interval

print(ret)