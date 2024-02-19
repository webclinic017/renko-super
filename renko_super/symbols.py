import pandas as pd
from constants import FUTL


class Symbols:
    def __init__(self, exch: str, symbol: str,
                 expiry: str, diff: int):
        self.exch = exch
        self.symbol = symbol
        self.expiry = expiry
        self.diff = diff
        self.csvfile = f"./map_{self.symbol.lower()}.csv"

    def get_exchange_token_map_finvasia(self):
        if FUTL.is_file_not_2day(self.csvfile):
            url = f"https://api.shoonya.com/{self.exch}_symbols.txt.zip"
            print(f"{url}")
            df = pd.read_csv(url)
            # filter the response
            df = df[
                (df["Exchange"] == self.exch)
                & (df["Symbol"] == self.symbol)
                # & (df["TradingSymbol"].str.contains(self.symbol + self.expiry))
            ][["Token", "TradingSymbol"]]
            # split columns with necessary values
            df[["Symbol", "Expiry", "OptionType", "StrikePrice"]] = df[
                "TradingSymbol"
            ].str.extract(r"([A-Z]+)(\d+[A-Z]+\d+)([CP])(\d+)")
            df.to_csv(self.csvfile, index=False)

    def get_atm(self, ltp) -> int:
        current_strike = ltp - (ltp % self.diff)
        next_higher_strike = current_strike + self.diff
        if ltp - current_strike < next_higher_strike - ltp:
            return int(current_strike)
        return int(next_higher_strike)

    def find_itm_option(self,
                        atm_strike: int,
                        ce_or_pe: str) -> str:
        if ce_or_pe == "C":
            return self.symbol + self.expiry + ce_or_pe + \
                str(atm_strike - self.diff)
        else:
            return self.symbol + self.expiry + ce_or_pe + \
                str(atm_strike + self.diff)

    def get_all_tokens_from_csv(self):
        df = pd.read_csv(self.csvfile)
        dct = dict(zip(df["TradingSymbol"], df["Token"]))
        return dct


if __name__ == "__main__":
    from constants import logging, SETG
    SYMBOL = "BANKNIFTY"
    try:
        symbols = Symbols("NFO", SYMBOL, SETG[SYMBOL]["expiry"])
        symbols.get_exchange_token_map_finvasia()
        dct = symbols.get_all_tokens_from_csv()
        print(dct["BANKNIFTY29FEB24C48000"])
    except Exception as e:
        logging.debug(f"{e} while getting symbols")
