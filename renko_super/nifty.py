from constants import logging, BRKR
from omspy_brokers.finvasia import Finvasia
from wserver import Wserver
import sys
from time import sleep
import pandas as pd
from constants import DATA
import mplfinance as mpf
import pandas as pd
from matplotlib import animation
from renkodf import RenkoWS
from datetime import datetime as dt
import streaming_indicators as si
from termcolor import colored as cl
from supertrend import get_supertrend

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


def animate(ival):

    if (0 + ival) >= len(df_ticks):
        print('no more data to plot')
        ani.event_source.interval *= 3
        if ani.event_source.interval > 12000:
            exit()
        return

    quotes = wserver.ltp
    for key, value in quotes.items():
        dct = {"timestamp": dt.now().timestamp(), "Symbol": key, "close": value}
    df_ticks.loc[len(df_ticks)] = dct
    timestamp = df_ticks['timestamp'].iat[(0 + ival)]
    price = df_ticks['close'].iat[(0 + ival)]
    r.add_prices(timestamp, price)
    tsla = r.renko_animate('normal', max_len=25, keep=10)
    print(tsla.head(3))
    """
    for idx, candle in df_normal.iterrows():
        st = ST.update(candle)
    print(st)
    tsla['st'], tsla['s_upt'], tsla['st_dt'] = get_supertrend(
        tsla['high'], tsla['low'], tsla['close'], 10, 3)
    print(tsla.tail())
    tsla = tsla[1:]

    # SUPERTREND PLOT
    ic = [
        #Supertrend
        mpf.make_addplot(tsla['s_upt'],color = 'green'),
        mpf.make_addplot(tsla['st_dt'],color = '#FF8849'),
    ]
    """
    ax1.clear()
    ax2.clear()
    mpf.plot(
        tsla,
        type='candle',
        ax=ax1,
        volume=ax2,
        axtitle='renko: normal')
    # plot green color line with width 2


ani = animation.FuncAnimation(fig, animate, interval=80)
mpf.show()
