import logging
import time


# sample
logging.basicConfig(level=logging.INFO)

PAPER_ATM = 47500


class Wserver:
    # flag to tell us if the websocket is open
    socket_opened = False
    ltp = {}

    def __init__(self, broker, tokens, dct_tokens):
        self.api = broker.finvasia
        self.tokens = tokens
        self.dct_tokens = dct_tokens
        ret = self.api.start_websocket(
            order_update_callback=self.event_handler_order_update,
            subscribe_callback=self.event_handler_quote_update,
            socket_open_callback=self.open_callback,
        )
        if ret:
            logging.debug(f"{ret} ws started")

    def open_callback(self):
        self.socket_opened = True
        print("app is connected")
        self.api.subscribe(self.tokens, feed_type="d")
        # api.subscribe(['NSE|22', 'BSE|522032'])

    # application callbacks
    def event_handler_order_update(self, message):
        logging.info("order event: " + str(message))

    def event_handler_quote_update(self, message):
        # e   Exchange
        # tk  Token
        # lp  LTP
        # pc  Percentage change
        # v   volume
        # o   Open price
        # h   High price
        # l   Low price
        # c   Close price
        # ap  Average trade price
        #
        logging.debug(
            "quote event: {0}".format(time.strftime(
                "%d-%m-%Y %H:%M:%S")) + str(message)
        )
        val = message.get("lp", False)
        if val:
            exch_tkn = message["e"] + "|" + message["tk"]
            self.ltp[self.dct_tokens[exch_tkn]] = float(val)


if __name__ == "__main__":
    from omspy_brokers.finvasia import Finvasia
    from constants import logging, BRKR, SETG
    from time import sleep
    import pandas as pd

    slp = 2
    SYMBOL = "BANKNIFTY"

    def get_api_and_wserver():
        api = Finvasia(**BRKR)
        if not api.authenticate():
            logging.error("Failed to authenticate")
            __import__("sys").exit(0)
        else:
            dct_tokens = {SETG[SYMBOL]['key']: SYMBOL}
            lst_tokens = list(dct_tokens.keys())
            wserver = Wserver(api, lst_tokens, dct_tokens)
        return api, wserver

    brkr, wserver = get_api_and_wserver()
    print(pd.DataFrame(brkr.orders))
    print(pd.DataFrame(brkr.positions))
    while True:
        print(wserver.ltp)
        sleep(1)
