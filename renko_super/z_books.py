from omspy_brokers.finvasia import Finvasia
from constants import BRKR
import pandas as pd

brkr = Finvasia(**BRKR)
if not brkr.authenticate():
    print("failed to auth")
    SystemExit(1)
else:
    print("success")


def orders():
    ord = []
    ord = brkr.orders
    if any(ord):
        for d in ord:
            if "remarks" not in d:
                d["remarks"] = 'no tag'
    keys = [
        "order_id",
        "broker_timestamp",
        "symbol",
        "side",
        "average_price",
        "status",
        "filled_quantity",
        "remarks"
    ]
    if any(ord):
        ord = [{k: d[k] for k in keys} for d in ord]
    print(pd.DataFrame(ord))


def positions():
    positions = []
    positions = brkr.positions
    keys = [
        "symbol",
        "quantity",
        "last_price",
        "urmtom",
        "rpnl",
    ]
    if any(positions):
        # filter by dict keys
        positions = [{key: dct[key] for key in keys} for dct in positions]
    print(pd.DataFrame(positions))


ltp = brkr.finvasia.get_quotes("NFO", "45860")
print(ltp)
orders()
positions()
