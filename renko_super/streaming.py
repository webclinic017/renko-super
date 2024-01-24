from constants import logging, BRKR
from omspy_brokers.finvasia import Finvasia
from wserver import Wserver
import sys
from time import sleep


def get_brkr_and_wserver():
    if any(BRKR):
        brkr = Finvasia(**BRKR)
        if not brkr.authenticate():
            logging.error("Failed to authenticate")
            sys.exit(0)
        else:
            dct_tokens = {"NSE|10005": "NSE"}
            lst_tokens = list(dct_tokens.keys())
            wserver = Wserver(brkr, lst_tokens, dct_tokens)
    return brkr, wserver


brkr, wserver = get_brkr_and_wserver()
while True:
    print(wserver.ltp)
    sleep(1)
