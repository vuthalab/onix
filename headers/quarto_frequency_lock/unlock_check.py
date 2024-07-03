from onix.headers.quarto_frequency_lock import Quarto
from onix.headers.find_quarto import find_quarto
import time

laser = Quarto(find_quarto("frequency", return_all = True)[0])

def run_expt_check_lock(run_expt_function, wait_between_attempts = 1):
    """
    Checks lock state. If locked, runs experiment. If the unlock counter increases during experiment, it will re-run the experiment. Waits for wait_between_attempts seconds
    before attempting to run experiment again.
    """
    while True:
        locked1, counter1 = laser.check_lock()
        if locked1:
            run_expt_function()
            locked2, counter2 = laser.check_lock(0.3)
            if counter1 == counter2:
                break
        time.sleep(wait_between_attempts)


