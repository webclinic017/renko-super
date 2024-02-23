from omspy_brokers.finvasia import Finvasia
from constants import BRKR, DATA
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
    df = pd.DataFrame(ord)
    print(pd.DataFrame(ord))
    df.to_csv(f"{DATA}orders.csv", index=False)


def positions(search=None):
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
        if search:
            positions = [
                dct for dct in positions if dct['symbol'].beginswith(search)]
    print(pd.DataFrame(positions))


orders()
positions()
