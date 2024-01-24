import pandas as pd
from renkodf import Renko
import mplfinance as mpf
from constants import DATA

SYMBOL = "BANKNIFTY24JANFUT"
BRICK = 10
INPUT = DATA + '2024-01-12-index-nfo-data.feather'
CONVERT = DATA + SYMBOL + ".csv"
RENKO = f"{DATA}{SYMBOL}{BRICK}_brick.csv"

df_ticks = pd.read_feather(INPUT)
if SYMBOL in df_ticks["symbol"].values:
    # df_ticks.rename(columns={'bid': 'close'}, inplace=True)
    df_ticks = df_ticks[df_ticks["symbol"] ==
                        SYMBOL].to_csv(CONVERT, index=False)
    # keep only columns with close price from df_ticks

df_ticks = pd.read_csv(CONVERT)
df_ticks = df_ticks[['close']].reset_index(drop=True)
print(df_ticks.head(3))

r = Renko(df_ticks, brick_size=BRICK)
df_renko = r.renko_df('normal')  # 'wicks' = default
df_renko.to_csv(RENKO, index=False)
print(df_renko.head(3))

mpf.plot(df_renko, type='candle', volume=False, style="charles",
         title=f"renko: normal\nbrick size: {BRICK}")
mpf.show()
# same as:
# r.plot('normal')
