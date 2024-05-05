import pandas as pd
from constants import DATA, FUTL

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
    "MIDCPNIFTY": {
        "diff": 100,
        "index": "NIFTY MID SELECT",
        "exch": "NSE",
        "token": "26074",
        "depth": 21,
    },
    "FINNIFTY": {
        "diff": 50,
        "index": "Nifty Fin Services",
        "exch": "NSE",
        "token": "26037",
        "depth": 16,
    },
}


class Symbols:
    def __init__(self, exch: str, symbol: str, expiry: str):
        self.exch = exch
        self.symbol = symbol
        self.expiry = expiry
        self.csvfile = f"{DATA}/{symbol}/map_{symbol.lower()}.csv"

    def get_exchange_token_map_finvasia(self):
        if FUTL.is_file_not_2day(self.csvfile):
            url = f"https://api.shoonya.com/{self.exch}_symbols.txt.zip"
            df = pd.read_csv(url)
            # filter the response
            df = df[
                (df["Exchange"] == self.exch) & (df["Symbol"] == self.symbol)
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

    """
    def find_itm_option(self, atm_strike: int, ce_or_pe: str) -> str:
        if ce_or_pe == "C":
            return self.symbol + self.expiry + ce_or_pe + str(atm_strike - self.diff)
        else:
            return self.symbol + self.expiry + ce_or_pe + str(atm_strike + self.diff)
    """

    def find_option(self, atm, c_or_p, distance):
        if c_or_p == "C":
            return f'{self.symbol}{self.expiry}{c_or_p}{atm + (distance * dct_sym[self.symbol]["diff"])}'
        else:
            return f'{self.symbol}{self.expiry}{c_or_p}{atm + (distance * dct_sym[self.symbol]["diff"])}'

    def get_all_tokens_from_csv(self):
        df = pd.read_csv(self.csvfile)
        dct = dict(zip(df["TradingSymbol"], df["Token"]))
        return dct


if __name__ == "__main__":
    from constants import logging, SETG

    SYMBOL = "BANKNIFTY"
    try:
        symbols = Symbols("NFO", SYMBOL, SETG[SYMBOL]["expiry"], SETG[SYMBOL]["diff"])
        symbols.get_exchange_token_map_finvasia()
        dct = symbols.get_all_tokens_from_csv()
        print(dct["BANKNIFTY08MAY24C48000"])

        atm = symbols.get_atm(48000.50)
        symbols.find_itm_option(atm, "C")
    except Exception as e:
        logging.debug(f"{e} while getting symbols")
