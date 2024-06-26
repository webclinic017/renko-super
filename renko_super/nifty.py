from constants import logging, BRKR, DATA, FUTL, SETG, SUPR
from toolkit.kokoo import is_time_past, blink, timer
from symbols import Symbols
from renkodf import RenkoWS
import streaming_indicators as si
import mplfinance as mpf
from matplotlib import animation
from datetime import datetime as dt
import pandas as pd
import numpy as np
import traceback
import copy
import downloader
from login import get_api


def read_positions_fm_file():
    """
    read overnight positions from file
    """
    D_POS = dict(
        symbol="",
        quantity=0,
        entry_price=0,
        last_price=0,
        urmtom=0,
        rpnl=0,
    )
    if FUTL.is_file_exists(F_POS):
        pos = FUTL.read_file(F_POS)
        D_POS.update(pos)
    return D_POS


try:
    SYMBOL = __import__("os").path.basename(__file__).split(".")[0].upper()
    EXPIRY = SETG[SYMBOL]["expiry"]
    DIFF = SETG[SYMBOL]["diff"]
    GFX = SETG["common"]["graphics"]
    EOD = SETG["common"]["eod"]
    O_SYM = Symbols("NFO", SYMBOL, EXPIRY)
    O_API = get_api(BRKR, LIVE=SETG["common"]["live"])
    # SYSTEM CONSTANTS
    DATA = DATA + SYMBOL + "/"
    F_HIST = DATA + "history.csv"
    if not FUTL.is_file_exists(F_HIST):
        print(f"We need {F_HIST} before continuing")
    F_POS = DATA + "position.json"
    F_SIGN = DATA + "signals.csv"
    D_POS = read_positions_fm_file()
except Exception as e:
    D_POS = dict(
        symbol="",
        quantity=0,
        entry_price=0,
        last_price=0,
        urmtom=0,
        rpnl=0,
    )
    logging.critical(f"{e} while initiating")
    print(traceback.format_exc())
    __import__("sys").exit(1)

G_MODE_TRADE = False
MAGIC = 15


def is_market():
    timer(1)
    if is_time_past(EOD):
        try:
            downloader.main()
        except Exception as e:
            print(e)
        __import__("sys").exit(0)
    return True


def call_or_put_pos() -> str:
    pos = ""
    try:
        length = len(SYMBOL) + 7
        if len(D_POS["symbol"]) > length:
            pos = D_POS["symbol"][length]
    except Exception as e:
        logging.debug(f"{e} while getting option type")
    finally:
        logging.debug(f"{D_POS['symbol']} call_or_put_pos: {pos}")
        return pos


def strip_positions(symbol):
    position = {}
    keys = [
        "symbol",
        "quantity",
        "last_price",
        "urmtom",
        "rpnl",
    ]
    if any(lst_pos := O_API.positions):
        lst_pos = [{key: dct[key] for key in keys} for dct in lst_pos]
        lst_pos = [
            dct for dct in lst_pos if dct["symbol"] == symbol and dct["quantity"] != 0
        ]
        logging.debug(f"found position {lst_pos=} from book")
        if any(lst_pos):
            position = lst_pos[0]
    return position


def _cls_pos_get_qty():
    dct = copy.deepcopy(SETG[SYMBOL])
    qty_fm_stg = dct.pop("quantity")
    try:
        dct = strip_positions(D_POS["symbol"])
        # if the position is found calculate pnl
        if any(dct):
            entry_price = float(D_POS["entry_price"])
            last_price = float(D_POS["last_price"])
            # checking if the entry price is factory set
            if (entry_price > 0) and (last_price > entry_price):
                # mutliply lot if profitable
                qty_fm_stg = 2 * SETG[SYMBOL]["quantity"]

            # either way close the position
            args = dict(
                symbol=dct["symbol"],
                quantity=dct["quantity"],
                disclosed_quantity=dct["quantity"],
                product="M",
                order_type="MKT",
                side="S",
                exchange="NFO",
                tag="renko_super",
            )
            resp = O_API.order_place(**args)
            logging.debug(f"{resp=} while closing positions {args=}")
    except Exception as e:
        logging.error(f"{e} while closing position .. {qty_fm_stg=}")
        print(traceback.format_exc())
    finally:
        return qty_fm_stg


def _write_signal_to_file(dets):
    headers = dets.columns.tolist()
    if FUTL.is_file_exists(F_SIGN):
        dets.to_csv(F_SIGN, mode="a", header=None, index=False)
    else:
        dets.to_csv(F_SIGN, mode="w", header=headers, index=False)


def _enter_and_write(symbol: str, quantity: int):
    try:
        position = {}
        args = dict(
            symbol=symbol,
            quantity=quantity,
            disclosed_quantity=quantity,
            product="M",
            order_type="MKT",
            side="B",
            exchange="NFO",
            tag="renko_super",
        )
        resp = O_API.order_place(**args)
        logging.debug(f"enter position {args=} got {resp=}")
        position = strip_positions(symbol)
        if any(position):
            position["entry_price"] = position["last_price"]
            FUTL.write_file(F_POS, position)
    except Exception as e:
        logging.error(f"{e} while entering position")
        print(traceback.format_exc())
    finally:
        return position


def do(dets, opt: str):
    atm = O_SYM.get_atm(dets.iloc[-1]["close"])
    itm_option = O_SYM.find_option(atm, opt, SETG[SYMBOL]["diff"])
    logging.debug(f"{atm=} {itm_option=}")
    new_pos = _enter_and_write(itm_option, _cls_pos_get_qty())
    dets["tx"] = opt
    _write_signal_to_file(dets)
    return new_pos


def get_ltp(api, symbol_token=None):
    blink()
    quote = 0
    try:
        if symbol_token:
            exchange = "NFO"
            symbol_token = str(symbol_token)
        else:
            exchange = SETG[SYMBOL]["key"].split("|")[0]
            symbol_token = SETG[SYMBOL]["key"].split("|")[1]
        resp = api.finvasia.get_quotes(exchange, symbol_token)
        quote = float(resp["lp"])
    except Exception as e:
        logging.warning(f"{e} while getting ltp for {symbol_token=} {exchange=}")
        traceback.print_exc()
    finally:
        return quote


def split_colors(st: pd.DataFrame):
    global G_MODE_TRADE
    try:
        new_pos = {}
        UP = []
        DN = []
        for i in range(len(st)):
            if st["st_dir"].iloc[i] == 1:
                UP.append(st["st"].iloc[i])
                DN.append(np.nan)
            elif st["st_dir"].iloc[i] == -1:
                DN.append(st["st"].iloc[i])
                UP.append(np.nan)
            else:
                UP.append(np.nan)
                DN.append(np.nan)
        st["up"] = UP
        st["dn"] = DN

        if len(st) > 1:
            dets = st.iloc[-2:-1].copy()
            dets["timestamp"] = dt.now()
            dets.drop(columns=["high", "low", "up", "dn", "st_dir"], inplace=True)

            # we are not live yet
            if not G_MODE_TRADE:
                if st.iloc[-1]["volume"] > MAGIC:
                    G_MODE_TRADE = True
                    if st.iloc[-1]["st_dir"] == 1 and call_or_put_pos() != "C":
                        new_pos = do(dets, "C")
                    elif st.iloc[-1]["st_dir"] == -1 and call_or_put_pos() != "P":
                        new_pos = do(dets, "P")
            else:
                if (
                    dets.iloc[-1]["close"] > dets.iloc[-1]["st"]
                    and call_or_put_pos() != "C"
                    and dets.iloc[-1]["close"] > dets.iloc[-1]["open"]
                ):
                    new_pos = do(dets, "C")
                elif (
                    dets.iloc[-1]["close"] < dets.iloc[-1]["st"]
                    and call_or_put_pos() != "P"
                    and dets.iloc[-1]["close"] < dets.iloc[-1]["open"]
                ):
                    new_pos = do(dets, "P")
                print("Signals \n", dets)
            print("Data \n", st.tail(2))
        print(f"Ready to take Trade ? {G_MODE_TRADE}")
    except Exception as e:
        logging.warning(f"{e} while splitting colors")
        traceback.print_exc()
    return st, new_pos


def run():
    O_SYM.get_exchange_token_map_finvasia()
    dct_symtkns = O_SYM.get_all_tokens_from_csv()
    df_ticks = pd.read_csv(F_HIST)
    r = RenkoWS(
        df_ticks["timestamp"].iat[0],
        df_ticks["close"].iat[0],
        brick_size=SETG[SYMBOL]["brick"],
    )
    initial_df = r.initial_df
    # init super trend streaming indicator
    ST = si.SuperTrend(SUPR["atr"], SUPR["multiplier"])

    def common_func(ival=None):
        df_normal = pd.DataFrame()
        try:
            if not ival:
                ival = len(df_ticks)

            ulying = get_ltp(O_API)
            if ulying == 0:
                return df_normal

            df_ticks.loc[len(df_ticks)] = {
                "timestamp": dt.now().timestamp(),
                "Symbol": SYMBOL,
                "close": ulying,
            }
            r.add_prices(
                df_ticks["timestamp"].iat[(0 + ival)], df_ticks["close"].iat[(0 + ival)]
            )
            df_normal = r.renko_animate("normal", max_len=MAGIC, keep=MAGIC - 1)
            for key, candle in df_normal.iterrows():
                st_dir, st = ST.update(candle)
                # add the st value to respective row
                # in the dataframe
                df_normal.loc[key, "st"] = st
                df_normal.loc[key, "st_dir"] = st_dir
            # get direction and split colors of supertrend
            df_normal, new_pos = split_colors(df_normal)
            # df_normal.to_csv(DATA + "df_normal.csv")
            # update positions if they are available
            if any(new_pos):
                logging.debug(f"found {new_pos=}")
                D_POS.update(new_pos)

            # update last_price and urmtom
            if len(D_POS["symbol"]) > 5:
                token = dct_symtkns[D_POS["symbol"]]
                last_price = get_ltp(O_API, token)
                pnl = float(last_price) - float(D_POS["entry_price"])
                urmtom = int(D_POS["quantity"]) * pnl
                updates = {"last_price": last_price, "urmtom": urmtom}
                D_POS.update(updates)
                # pd.DataFrame(D_POS, index=[0]).to_csv(DATA + "positions_v1.csv")
                print("Positions \n", pd.DataFrame(D_POS, index=[0]))

        except Exception as e:
            logging.error(f"{e} while common func")
            print(e)
        finally:
            return df_normal

    def animate(ival):
        if (0 + ival) >= len(df_ticks):
            logging.error("no more data to plot")
            ani.event_source.interval *= 3
            if ani.event_source.interval > 12000:
                exit()
            return

        df_normal = common_func(ival)

        if df_normal is None:
            return
        # clear everytime
        ax1.clear()
        ax2.clear()
        ic = [
            # Supertrend
            mpf.make_addplot(
                df_normal[["up"]],
                color="green",
                ax=ax1,
            ),
            mpf.make_addplot(
                df_normal[["dn"]],
                color="#FF8849",
                ax=ax1,
            ),
        ]
        mpf.plot(
            df_normal, type="candle", addplot=ic, ax=ax1, volume=ax2, axtitle=SYMBOL
        )
        _ = is_market()

    if not GFX:
        while is_market():
            _ = common_func(0)
    else:
        # init plot
        fig, axes = mpf.plot(
            initial_df,
            returnfig=True,
            volume=True,
            figsize=(11, 8),
            panel_ratios=(2, 1),
            type="candle",
            style="charles",
        )
        ax1 = axes[0]
        ax2 = axes[2]
        mpf.plot(initial_df, type="candle", ax=ax1, volume=ax2, axtitle="renko: normal")
        ani = animation.FuncAnimation(fig, animate, interval=80)
        mpf.show()


if __name__ == "__main__":
    run()
