from omspy_brokers.finvasia import Finvasia
from paper import Paper
import traceback


def get_api(CNFG, LIVE=False):
    try:
        if LIVE:
            print("LIVE mode is ON")
            api = Finvasia(**CNFG)
        else:
            print("PAPER trading")
            api = Paper(**CNFG)

        if not api.authenticate():
            raise Exception("failed to authenticate")
        else:
            print("authenticated")
    except Exception as e:
        print(f"EXCEPTION: WHILE LOGGING IN \n {e}")
        traceback.print_exc()
        __import__("sys").exit(1)
    return api


if __name__ == "__main__":
    from constants import BRKR

    obj = get_api(BRKR)
    print(obj.positions)
