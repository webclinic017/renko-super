from omspy_brokers.finvasia import Finvasia
from paper import Paper
import traceback


def get_api(CNFG, LIVE=False):
    try:
        if LIVE:
            api = Finvasia(**CNFG)
        else:
            api = Paper(**CNFG)
        if not api.authenticate():
            print("failed to authenticate")
            SystemExit()
    except Exception as e:
        print(f"EXCEPTION: WHILE LOGGING IN \n {e}")
        traceback.print_exc()
    return api