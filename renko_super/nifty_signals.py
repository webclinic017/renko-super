from constants import logging, BRKR, DATA, SETG, SUPR, UTLS
from wserver import Wserver
from omspy_brokers.finvasia import Finvasia
from renkodf import RenkoWS
import streaming_indicators as si
import mplfinance as mpf
from matplotlib import animation
from datetime import datetime as dt
import pendulum
import pandas as pd
import numpy as np

SYMBOL = "NIFTY 50"


def get_brkr_and_wserver():
    if any(BRKR):
        brkr = Finvasia(**BRKR)
        if not brkr.authenticate():
            logging.error("Failed to authenticate")
            __import__("sys").exit(0)
        else:
            dct_tokens = {SETG[SYMBOL]['key']: SYMBOL}
            lst_tokens = list(dct_tokens.keys())
            wserver = Wserver(brkr, lst_tokens, dct_tokens)
    return brkr, wserver


def color(st: pd.DataFrame) -> pd.DataFrame:
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


i = 0


def animate(ival):
    global i
    i += 1
    # sanity checks
    if (0 + ival) >= len(df_ticks):
        print('no more data to plot')
        ani.event_source.interval *= 3
        if ani.event_source.interval > 12000:
            exit()
        return

    if i == len(df_ticks):
        # get streaming data from broker wsocket
        quotes = wserver.ltp
        dct = [{
            "timestamp": dt.now().timestamp(),
            "Symbol": SYMBOL,
            "close": quotes[SYMBOL]}
            for SYMBOL in quotes.keys()][0]

        # update only when you have data
        if any(dct):
            df_ticks.loc[len(df_ticks)] = dct
            timestamp = df_ticks['timestamp'].iat[(0 + ival)]
            price = df_ticks['close'].iat[(0 + ival)]
            r.add_prices(timestamp, price)

    # get renko dataframe
    df_normal = r.renko_animate('normal', max_len=26, keep=25)
    for key, candle in df_normal.iterrows():
        dir, st = ST.update(candle)
        # add the st value to respective row
        # in the dataframe
        df_normal.loc[key, 'st'] = st
        df_normal.loc[key, 'dir'] = dir

    # get direction and color of supertrend
    df_normal = color(df_normal)
    # drop unwanted columns
    df_normal.drop(columns=['dir', 'st'], inplace=True)

    # clear everytime
    ax1.clear()
    ax2.clear()
    ic = [
        # Supertrend
        mpf.make_addplot(df_normal[['up']], color='green', ax=ax1,),
        mpf.make_addplot(df_normal[['dn']], color='#FF8849', ax=ax1,),
    ]
    mpf.plot(
        df_normal,
        type='candle',
        addplot=ic,
        ax=ax1,
        volume=ax2,
        axtitle=SYMBOL)


# check if you are getting data from sockets
brkr, wserver = get_brkr_and_wserver()
quotes = {}
while not any(quotes):
    # dataframe from dictionary
    quotes = wserver.ltp
    UTLS.slp_til_nxt_sec()

df_ticks = pd.read_csv(f"{DATA}{SYMBOL.replace(' ', '_')}.csv")
print(df_ticks.head())

r = RenkoWS(
    df_ticks['timestamp'].iat[0],
    df_ticks['close'].iat[0],
    brick_size=SETG[SYMBOL]['brick']
)
initial_df = r.initial_df
# init plot
fig, axes = mpf.plot(initial_df, volume=True,
                     title='\n' + SYMBOL,
                     type='candle', style='charles')
ax1 = axes[0]
ax2 = axes[2]
mpf.plot(initial_df, ax=ax1, volume=ax2)
# init super trend streaming indicator
ST = si.SuperTrend(SUPR['atr'], SUPR['multiplier'])

ani = animation.FuncAnimation(
    fig, animate, interval=80, save_count=100)
print(ani)
mpf.show()
