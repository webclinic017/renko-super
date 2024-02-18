import pandas as pd
import re
from constants import FUTL

dct_sym = {
    "NIFTY": {
        "diff": 50,
        "index": "Nifty 50",
        "exch": "NSE",
        "token": "26000",
        "depth": 16,
    },
    "BANKNIFTY": {
        "diff": 100,
        "index": "Nifty Bank",
        "exch": "NSE",
        "token": "26009",
        "depth": 25,
    },
}


class Symbols:
    def __init__(self, exch, symbol: str, expiry: str):
        self.exch = exch
        self.symbol = symbol
        self.expiry = expiry
        self.csvfile = f"./map_{self.symbol.lower()}.csv"

    def get_exchange_token_map_finvasia(self):
        if FUTL.is_file_not_2day(self.csvfile):
            url = f"https://api.shoonya.com/{self.exch}_symbols.txt.zip"
            print(f"{url}")
            df = pd.read_csv(url)
            # filter the response
            df = df[
                (df["Exchange"] == self.exch)
                # & (df["TradingSymbol"].str.contains(self.symbol + self.expiry))
            ][["Token", "TradingSymbol"]]
            # split columns with necessary values
            df[["Symbol", "Expiry", "OptionType", "StrikePrice"]] = df[
                "TradingSymbol"
            ].str.extract(r"([A-Z]+)(\d+[A-Z]+\d+)([CP])(\d+)")
            df.to_csv(self.csvfile, index=False)

    def get_atm(self, ltp) -> int:
        current_strike = ltp - (ltp % dct_sym[self.symbol]["diff"])
        next_higher_strike = current_strike + dct_sym[self.symbol]["diff"]
        if ltp - current_strike < next_higher_strike - ltp:
            return int(current_strike)
        return int(next_higher_strike)

    def get_tokens(self, strike):
        df = pd.read_csv(self.csvfile)
        lst = []
        lst.append(self.symbol + self.expiry + "C" + str(strike))
        lst.append(self.symbol + self.expiry + "P" + str(strike))
        for v in range(1, dct_sym[self.symbol]["depth"]):
            lst.append(
                self.symbol
                + self.expiry
                + "C"
                + str(strike + v * dct_sym[self.symbol]["diff"])
            )
            lst.append(
                self.symbol
                + self.expiry
                + "P"
                + str(strike + v * dct_sym[self.symbol]["diff"])
            )
            lst.append(
                self.symbol
                + self.expiry
                + "C"
                + str(strike - v * dct_sym[self.symbol]["diff"])
            )
            lst.append(
                self.symbol
                + self.expiry
                + "P"
                + str(strike - v * dct_sym[self.symbol]["diff"])
            )

        df["Exchange"] = self.exch
        tokens_found = (
            df[df["TradingSymbol"].isin(lst)]
            .assign(tknexc=df["Exchange"] + "|" + df["Token"].astype(str))[
                ["tknexc", "TradingSymbol"]
            ]
            .set_index("tknexc")
        )
        dct = tokens_found.to_dict()
        return dct["TradingSymbol"]

    def find_option_type(self, tradingsymbol: str) -> str:
        option_pattern = re.compile(rf"{self.symbol}{self.expiry}([CP])\d+")
        match = option_pattern.match(tradingsymbol)
        if match:
            return match.group(1)  # Returns 'C' for call, 'P' for put
        else:
            return ""

    def find_itm_option(self,
                        atm_strike: int,
                        ce_or_pe: str,
                        depth: int) -> str:
        if ce_or_pe == "C":
            return self.symbol + self.expiry + ce_or_pe + \
                str(atm_strike - depth)
        elif ce_or_pe == "P":
            return self.symbol + self.expiry + ce_or_pe + \
                str(atm_strike - depth)
        return ""


if __name__ == "__main__":
    from constants import logging, SETG
    SYMBOL = "BANKNIFTY"
    try:
        symbols = Symbols("NFO", SYMBOL, SETG[SYMBOL]["expiry"])
        symbols.get_exchange_token_map_finvasia()
        print(symbols.get_tokens(47000))
        print(symbols.find_option_type(
            SYMBOL + SETG[SYMBOL]["expiry"] + "C47000"))
    except Exception as e:
        logging.debug(f"{e} while getting symbols")
