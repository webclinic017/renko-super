from constants import logging, BRKR
from omspy_brokers.finvasia import Finvasia
from wserver import Wserver
import sys
from time import sleep
import pandas as pd
from constants import DATA
import mplfinance as mpf
from matplotlib import animation
from renkodf import RenkoWS
from datetime import datetime as dt
import streaming_indicators as si
import numpy as np

SYMBOL = "NIFTY 50"
BRICK = 10
INPUT = DATA + 'Nifty_23_01_24.feather'


def get_brkr_and_wserver():
    if any(BRKR):
        brkr = Finvasia(**BRKR)
        if not brkr.authenticate():
            logging.error("Failed to authenticate")
            sys.exit(0)
        else:
            dct_tokens = {"NSE|26000": SYMBOL}
            lst_tokens = list(dct_tokens.keys())
            wserver = Wserver(brkr, lst_tokens, dct_tokens)
    return brkr, wserver


brkr, wserver = get_brkr_and_wserver()
quotes = {}
while not any(quotes):
    # dataframe from dictionary
    quotes = wserver.ltp
    sleep(1)


BRICK = 10
df_ticks = pd.read_feather(INPUT)
print(df_ticks.head(3))
df_ticks = df_ticks[['Symbol', 'ClosePrice', 'TickTime']]
df_ticks['close'] = df_ticks.ClosePrice
# Convert 'datetime' column to Pandas datetime object
df_ticks['TickTime'] = pd.to_datetime(df_ticks['TickTime'])
# Calculate and add the timestamp to a new column 'timestamp'
df_ticks['timestamp'] = df_ticks['TickTime'].apply(lambda x: x.timestamp())
df_ticks.drop(columns=['TickTime', 'ClosePrice'], inplace=True)
initial_timestamp = df_ticks['timestamp'].iat[0]
initial_price = df_ticks['close'].iat[0]

r = RenkoWS(initial_timestamp, initial_price, brick_size=BRICK)
initial_df = r.initial_df

fig, axes = mpf.plot(initial_df, returnfig=True, volume=True,
                     figsize=(11, 8), panel_ratios=(2, 1),
                     title='\n' + SYMBOL, type='candle', style='charles')
ax1 = axes[0]
ax2 = axes[2]

mpf.plot(initial_df, type='candle', ax=ax1,
         volume=ax2, axtitle='renko: normal')

st_atr_length = 10
st_factor = 3
ST = si.SuperTrend(st_atr_length, st_factor)


def color2(st: pd.DataFrame) -> pd.DataFrame:
    UP = []
    DN = []
    for i in range(len(st)):
        if st['dir'].iloc[i] == 1:
            UP.append(st['st'].iloc[i])
            DN.append(np.nan)
        elif st['dir'].iloc[i] == -1:
            DN.append(st['st'].iloc[i])
            UP.append(np.nan)
        else:
            UP.append(np.nan)
            DN.append(np.nan)
    st['up'] = UP
    st['dn'] = DN
    return st


def animate(ival):
    if (0 + ival) >= len(df_ticks):
        print('no more data to plot')
        ani.event_source.interval *= 3
        if ani.event_source.interval > 12000:
            exit()
        return

    quotes = wserver.ltp
    dct = [{
        "timestamp": dt.now().timestamp(),
        "Symbol": SYMBOL,
        "close": quotes[SYMBOL]}
        for SYMBOL in quotes.keys()][0]
    if any(dct):
        df_ticks.loc[len(df_ticks)] = dct
    timestamp = df_ticks['timestamp'].iat[(0 + ival)]
    price = df_ticks['close'].iat[(0 + ival)]
    r.add_prices(timestamp, price)
    df_normal = r.renko_animate('normal', max_len=26, keep=25)
    for key, candle in df_normal.iterrows():
        dir, st = ST.update(candle)
        # add the st value to respective row
        # in the dataframe
        df_normal.loc[key, 'st'] = st
        df_normal.loc[key, 'dir'] = dir

    print(df_normal.tail(3))
    df_normal = color2(df_normal)
    up_super_trend = df_normal[['up']]
    dn = df_normal[['dn']]

    ax1.clear()
    ax2.clear()
    ic = [
        # Supertrend
        mpf.make_addplot(up_super_trend, color='green', ax=ax1,),
        mpf.make_addplot(dn, color='#FF8849', ax=ax1,),
    ]
    mpf.plot(
        df_normal,
        type='candle',
        addplot=ic,
        ax=ax1,
        volume=ax2,
        axtitle='renko: normal')


ani = animation.FuncAnimation(fig, animate, interval=80)
mpf.show()
