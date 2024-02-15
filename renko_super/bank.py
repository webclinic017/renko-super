from constants import logging, BRKR, DATA, SETG, SUPR, UTIL
from wserver import Wserver
from omspy_brokers.finvasia import Finvasia
from renkodf import RenkoWS
import streaming_indicators as si
import mplfinance as mpf
from matplotlib import animation
from datetime import datetime as dt
import pandas as pd
import numpy as np
import traceback
import os
from tabulate import tabulate

SYMBOL = "NIFTY BANK"

signal_details_file = "signal_details.csv"


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


def get_historical_data():
    # clean the input dataframe
    INPUT = DATA + 'Nifty_23_01_24.feather'
    df_ticks = pd.read_feather(INPUT)
    print(df_ticks.head(3))
    # select only necessary columns
    df_ticks = df_ticks[['Symbol', 'ClosePrice', 'TickTime']]
    df_ticks['close'] = df_ticks.ClosePrice
    # Convert 'datetime' column to Pandas datetime object
    df_ticks['TickTime'] = pd.to_datetime(df_ticks['TickTime'])
    # Calculate and add the timestamp to a new column 'timestamp'
    df_ticks['timestamp'] = df_ticks['TickTime'].apply(
        lambda x: x.timestamp())
    # drop unwanted columns
    df_ticks.drop(columns=['TickTime', 'ClosePrice'], inplace=True)
    # get timestamp and price for init RenkoWs
    return df_ticks


signal = ""


def color(st: pd.DataFrame) -> pd.DataFrame:
    global signal
    UP = []
    DN = []
    for i in range(len(st)):
        if st['st_dir'].iloc[i] == 1:
            UP.append(st['st'].iloc[i])
            DN.append(np.nan)
        elif st['st_dir'].iloc[i] == -1:
            DN.append(st['st'].iloc[i])
            UP.append(np.nan)
        else:
            UP.append(np.nan)
            DN.append(np.nan)
    st['up'] = UP
    st['dn'] = DN
    try:
        if len(st) > 0:
            headers = st.columns.to_list() + ["timestamp", "signal"]
            curr_close = st.iloc[-1]["close"]
            prev_st = st.iloc[-2]["st"]
            dets = st.iloc[-1:].copy()
            # overwrite st column
            dets["st"] = prev_st
            # append new column
            dets["timestamp"] = dt.now()
            dets.set_index("timestamp", inplace=True)
            dets.drop(columns=["open", "high", "low",
                      "up", "dn"], inplace=True)
            if curr_close > prev_st and signal != "buy":
                signal = "buy"
                # print(dets)
                if os.path.exists(signal_details_file):
                    dets.to_csv(signal_details_file, mode="a",
                                header=None, index=False)
                else:
                    dets.to_csv(signal_details_file, mode="w",
                                header=headers, index=False)
                # trigger buy order
            elif prev_st > curr_close and signal != "sell":
                signal = "sell"
                if os.path.exists(signal_details_file):
                    dets.to_csv(signal_details_file, mode="a",
                                header=None, index=False)
                else:
                    dets.to_csv(signal_details_file, mode="w",
                                header=headers, index=False)
            else:
                dets["signal"] = signal
                # trigger sell order
            print(tabulate(st.tail(5), headers='keys', tablefmt='psql'))
            print(tabulate(dets.tail(), headers='keys', tablefmt='psql'))
    except Exception as e:
        print(e)
        traceback.print_exc()
    return st


def animate(ival):
    # sanity checks
    if (0 + ival) >= len(df_ticks):
        print('no more data to plot')
        ani.event_source.interval *= 3
        if ani.event_source.interval > 12000:
            exit()
        return

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
        st_dir, st = ST.update(candle)
        # add the st value to respective row
        # in the dataframe
        df_normal.loc[key, 'st'] = st
        df_normal.loc[key, 'st_dir'] = st_dir

    # get direction and color of supertrend
    df_normal = color(df_normal)

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
    UTIL.slp_til_nxt_sec()

# df_ticks = get_historical_data()
df_ticks = pd.read_csv(f"{DATA}{SYMBOL.replace(' ', '_')}.csv")

r = RenkoWS(
    df_ticks['timestamp'].iat[0],
    df_ticks['close'].iat[0],
    brick_size=SETG[SYMBOL]['brick']
)
initial_df = r.initial_df
# init plot
fig, axes = mpf.plot(initial_df, returnfig=True, volume=True,
                     figsize=(11, 8), panel_ratios=(2, 1),
                     title='\n' + SYMBOL, type='candle', style='charles')
ax1 = axes[0]
ax2 = axes[2]
mpf.plot(initial_df, type='candle', ax=ax1,
         volume=ax2, axtitle='renko: normal')
# init super trend streaming indicator
ST = si.SuperTrend(SUPR['atr'], SUPR['multiplier'])

ani = animation.FuncAnimation(
    fig, animate, interval=80, save_count=100)
mpf.show()
