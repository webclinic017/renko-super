from constants import logging, BRKR, DATA, FUTL, SETG, SUPR, UTIL
from symbols import Symbols
from omspy_brokers.finvasia import Finvasia
from renkodf import RenkoWS
import streaming_indicators as si
import mplfinance as mpf
from matplotlib import animation
from datetime import datetime as dt
import pandas as pd
import numpy as np
import traceback
from rich import print

try:
    SYMBOL = __import__("os").path.basename(__file__).split(".")[0].upper()
    EXPIRY = SETG[SYMBOL]['expiry']
    DIFF = SETG[SYMBOL]['diff']
except Exception as e:
    logging.critical(f"{e} while getting constants")
    print(traceback.format_exc())
    __import__("sys").exit(1)

DATA += SYMBOL
F_HIST = DATA + "/history.csv"
F_POS = DATA + "/position.json"
F_SIGN = DATA + "/signals.csv"


def call_or_put_pos() -> str:
    pos = ""
    try:
        length = len(SYMBOL) + 7
        if len(D_POS['symbol']) > length:
            pos = D_POS['symbol'][length]
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
        lst_pos = [dct for dct in lst_pos if dct['symbol']
                   == symbol and dct['quantity'] != 0]
        logging.debug(f"found position {lst_pos=} from book")
        if any(lst_pos):
            position = lst_pos[0]
    return position


def _cls_pos_get_qty():
    qty_fm_stg = SETG[SYMBOL]['quantity']
    try:
        dct = strip_positions(D_POS["symbol"])
        # if the position is found calculate pnl
        if any(dct):
            entry_price = float(D_POS["entry_price"])
            last_price = float(D_POS["last_price"])
            # checking if the entry price is factory set
            if (
                entry_price > 0 and
                last_price > entry_price
            ):
                # mutliply lot if profitable
                qty_fm_stg *= 2

            # either way close the position
            args = dict(
                symbol=dct["symbol"],
                quantity=dct['quantity'],
                disclosed_quantity=dct['quantity'],
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
        dets.to_csv(F_SIGN, mode="a",
                    header=None, index=False)
    else:
        dets.to_csv(F_SIGN, mode="w",
                    header=headers, index=False)


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
    itm_option = O_SYM.find_itm_option(
        atm,
        opt)
    new_pos = _enter_and_write(
        itm_option,
        _cls_pos_get_qty()
    )
    dets["tx"] = opt
    _write_signal_to_file(dets)
    return new_pos


def get_ltp(api, symbol_token=None):
    UTIL.slp_til_nxt_sec()
    quote = 0
    try:
        if symbol_token:
            exchange = "NFO"
            symbol_token = str(symbol_token)
        else:
            exchange = SETG[SYMBOL]['key'].split("|")[0]
            symbol_token = SETG[SYMBOL]['key'].split("|")[1]
        resp = api.finvasia.get_quotes(exchange, symbol_token)
        if resp is None:
            raise Exception("No response")
        else:
            quote = int(float(resp["lp"]))
    except Exception as e:
        logging.warning(f"{e} while getting ltp for {symbol_token=}")
        print(traceback.format_exc())
    finally:
        return quote


def split_colors(st: pd.DataFrame):
    try:
        new_pos = {}
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
        if len(st) > 1 and st.iloc[-2]['volume'] > 25:
            dets = st.iloc[-2:].copy()
            dets["timestamp"] = dt.now()
            dets.drop(columns=["open", "high", "low",
                      "up", "dn", "st_dir"], inplace=True)
            if (
                dets.iloc[-1]["close"] > dets.iloc[-1]["st"] and
                    call_or_put_pos() != "C"):
                new_pos = do(dets, "C")
            elif (
                dets.iloc[-1]["close"] < dets.iloc[-1]["st"] and
                    call_or_put_pos() != "P"):
                new_pos = do(dets, "P")
            print("Signals \n", dets)
        print("Data \n", st.tail(2))
    except Exception as e:
        logging.warning(f"{e} while splitting colors")
        traceback.print_exc()
    return st, new_pos


def read_positions_fm_file():
    """
        read overnight positions from file
    """
    if FUTL.is_file_exists(F_POS):
        pos = FUTL.read_file(F_POS)
        D_POS.update(pos)


def get_api():
    brkr = Finvasia(**BRKR)
    if not brkr.authenticate():
        logging.error("Failed to authenticate")
        __import__("sys").exit(0)
    else:
        print("Authenticated")
        return brkr


D_POS = dict(
    symbol="",
    quantity=0,
    entry_price=0,
    last_price=0,
    urmtom=0,
    rpnl=0,
)
read_positions_fm_file()
O_SYM = Symbols("NFO", SYMBOL, EXPIRY, DIFF)
O_API = get_api()


def run():
    def animate(ival):
        if (0 + ival) >= len(df_ticks):
            logging.error('no more data to plot')
            ani.event_source.interval *= 3
            if ani.event_source.interval > 12000:
                exit()
            return
        ulying = get_ltp(O_API)
        if ulying == 0:
            return

        df_ticks.loc[len(df_ticks)] = {
            "timestamp": dt.now().timestamp(),
            "Symbol": SYMBOL,
            "close": ulying
        }
        r.add_prices(
            df_ticks['timestamp'].iat[(0 + ival)],
            df_ticks['close'].iat[(0 + ival)]
        )
        df_normal = r.renko_animate('normal', max_len=26, keep=25)
        for key, candle in df_normal.iterrows():
            st_dir, st = ST.update(candle)
            # add the st value to respective row
            # in the dataframe
            df_normal.loc[key, 'st'] = st
            df_normal.loc[key, 'st_dir'] = st_dir
        # get direction and split colors of supertrend
        df_normal, new_pos = split_colors(df_normal)
        # update positions if they are available
        if any(new_pos):
            logging.debug(f"found {new_pos=}")
            D_POS.update(new_pos)
        else:
            logging.debug("NO NEW POSITION YET")
        # update last_price and urmtom
        if len(D_POS["symbol"]) > 5:
            token = dct_symtkns[D_POS["symbol"]]
            last_price = get_ltp(O_API, token)
            pnl = float(last_price) - float(D_POS['entry_price'])
            urmtom = int(D_POS["quantity"]) * pnl
            updates = {
                "last_price": last_price,
                "urmtom": urmtom
            }
            D_POS.update(updates)
        print("Positions \n", pd.DataFrame(D_POS, index=[0]))
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

    """
        begins to run here
    """
    O_SYM.get_exchange_token_map_finvasia()
    dct_symtkns = O_SYM.get_all_tokens_from_csv()
    df_ticks = pd.read_csv(F_HIST)
    r = RenkoWS(
        df_ticks['timestamp'].iat[0],
        df_ticks['close'].iat[0],
        brick_size=SETG[SYMBOL]['brick']
    )
    initial_df = r.initial_df
    # init plot
    fig, axes = mpf.plot(initial_df, returnfig=True, volume=True,
                         figsize=(11, 8), panel_ratios=(2, 1),
                         type='candle', style='charles')
    ax1 = axes[0]
    ax2 = axes[2]
    mpf.plot(initial_df, type='candle', ax=ax1,
             volume=ax2, axtitle='renko: normal')
    # init super trend streaming indicator
    ST = si.SuperTrend(SUPR['atr'], SUPR['multiplier'])
    ani = animation.FuncAnimation(
        fig, animate, interval=80, save_count=100)
    mpf.show()


if __name__ == "__main__":
    run()


"""
def get_api_and_wserver(O_SYM):
    O_SYM.get_exchange_token_map_finvasia()
    brkr = Finvasia(**BRKR)
    if not brkr.authenticate():
        logging.error("Failed to authenticate")
        __import__("sys").exit(0)
    else:
        quote = get_ltp(brkr)
        if quote > 0:
            atm = O_SYM.get_atm(quote)
            dct_tokens = O_SYM.get_tokens(atm)
            print(dct_tokens)
            lst_tokens = list(dct_tokens.keys())
            print(lst_tokens)
            wserver = Wserver(brkr, lst_tokens, dct_tokens)
        else:
            logging.error("Failed to get quote")
            __import__("sys").exit(0)
    quotes = {}
    while not any(quotes):
        # dataframe from dictionary
        quotes = wserver.ltp
        UTIL.slp_til_nxt_sec()
    print(quotes)
    return brkr, wserver
"""
