import pandas as pd
from renkodf import Renko
import mplfinance as mpf

SYMBOL = "BANKNIFTY24JANFUT"
BRICK = 10
df_ticks = pd.read_feather('../2024-01-12-index-nfo-data.feather')
if SYMBOL in df_ticks["symbol"].values:
    # df_ticks.rename(columns={'bid': 'close'}, inplace=True)
    df_ticks = df_ticks[df_ticks["symbol"] ==
                        SYMBOL].to_csv(SYMBOL + ".csv", index=False)
    # keep only columns with close price from df_ticks

df_ticks = pd.read_csv(SYMBOL + ".csv")
df_ticks = df_ticks[['close']].reset_index(drop=True)
print(df_ticks.head(3))
r = Renko(df_ticks, brick_size=BRICK)
df_renko = r.renko_df('normal')  # 'wicks' = default
df_renko.to_csv(f"{SYMBOL}{BRICK}_brick.csv", index=False)
print(df_renko.head(3))
mpf.plot(df_renko, type='candle', volume=False, style="charles",
         title=f"renko: normal\nbrick size: {BRICK}")
mpf.show()
# same as:
# r.plot('normal')
