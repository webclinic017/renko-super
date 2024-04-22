from constants import BRKR, DATA, FUTL, SETG, SUPR, SMA_SETG
from symbols import Symbols
from login import get_api
from renkodf import RenkoWS
import streaming_indicators as si
from datetime import datetime as dt
import pandas as pd
import numpy as np
import traceback
import sys
import pendulum
from logzero import logger, logfile
from toolkit.kokoo import is_time_past, timer, blink

logfile("./renko_super.log")
IS_LIVE = False

try:
    SYMBOL = __import__("os").path.basename(__file__).split(".")[0].upper()
    if "_" in SYMBOL:
        SYMBOL = SYMBOL.split("_")[0]
    EXPIRY = SETG[SYMBOL]["expiry"]
    DIFF = SETG[SYMBOL]["diff"]
except Exception as e:
    logger.critical(f"{e} while getting constants")
    print(traceback.format_exc())
    __import__("sys").exit(1)

DATA += SYMBOL
F_HIST = DATA + "/history.csv"
F_POS = DATA + "/position.json"
F_SIGN = DATA + "/signals.csv"
SYMBOL_PURCHASED = None
is_live_ltp = False


def _write_signal_to_file(dets):
    headers = dets.columns.tolist()
    if FUTL.is_file_exists(F_SIGN):
        dets.to_csv(F_SIGN, mode="a", header=None, index=False)
    else:
        dets.to_csv(F_SIGN, mode="w", header=headers, index=False)


def place_api_order(dets, opt: str, action: str):
    logger.info(f"Into Place API Order {action} - {dets}, {opt}")
    quantity = SETG[SYMBOL]["quantity"]
    args = dict(
        symbol=opt,
        quantity=quantity,
        disclosed_quantity=quantity,
        product="M",
        order_type="MKT",
        side=action[0].upper(),
        exchange="NFO",
        tag="renko_super",
    )
    resp = O_API.order_place(**args)
    print(resp)
    dets["timestamp"] = pendulum.now().timestamp()
    dets["tx"] = opt[-6]
    _write_signal_to_file(dets)
    return args


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
        if resp is None:
            raise Exception("No response")
        else:
            quote = int(float(resp["lp"]))
    except Exception as e:
        logger.warning(f"{e} while getting ltp for {symbol_token=}")
        print(traceback.format_exc())
    finally:
        return quote


def split_colors(st: pd.DataFrame, option_name: str, df):
    global SYMBOL_PURCHASED, is_live_ltp
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
        st["col_num"] = list(range(len(st)))

        if len(st) > 2:
            dets = st.iloc[-3:-1].copy()
            dets["timestamp"] = dt.now()

            # we are not live yet
            if not SYMBOL_PURCHASED:
                if df.iloc[0]["historical_count"] < len(df):
                    is_live_ltp = True
                    # BUY CONDITION CHECK
                    if (
                        dets.iloc[-2]["sma"] is not None
                        and dets.iloc[-2]["up"] is not None
                        and dets.iloc[-2]["up"] > 0
                        and dets.iloc[-2]["open"] < dets.iloc[-2]["sma"]
                        and dets.iloc[-2]["close"] > dets.iloc[-2]["sma"]
                    ):
                        dets.drop(
                            columns=["high", "low", "up",
                                     "dn", "st_dir", "col_num"],
                            inplace=True,
                        )
                        new_pos = place_api_order(dets, option_name, "BUY")
                        SYMBOL_PURCHASED = option_name
                    elif (
                        dets.iloc[-2]["sma"] is not None
                        and dets.iloc[-2]["up"] is not None
                        and dets.iloc[-2]["open"] < dets.iloc[-2]["close"]
                        and dets.iloc[-2]["close"] > dets.iloc[-2]["sma"]
                        and dets.iloc[-2]["close"] > dets.iloc[-2]["up"]
                    ):
                        dets.drop(
                            columns=["high", "low", "up",
                                     "dn", "st_dir", "col_num"],
                            inplace=True,
                        )
                        new_pos = place_api_order(dets, option_name, "BUY")
                        SYMBOL_PURCHASED = option_name
                    print("Signals \n", dets)
                    logger.info(f"{new_pos=}")
                    return st, new_pos
            elif SYMBOL_PURCHASED == option_name:
                # SELL CONDITION CHECK
                if (
                    dets.iloc[-2]["sma"] is not None
                    and dets.iloc[-2]["open"] > dets.iloc[-2]["close"]
                    and dets.iloc[-2]["close"] < dets.iloc[-2]["sma"]
                ):
                    dets.drop(
                        columns=["high", "low", "up", "dn", "st_dir"], inplace=True
                    )
                    new_pos = place_api_order(dets, option_name, "SELL")
                    SYMBOL_PURCHASED = None
                print("Signals \n", dets)
                logger.info(f"{new_pos=}")
                return st, new_pos
            print("Data \n", st.tail(2))
        print(f"Ready to take Trade ? {is_live_ltp}")
    except Exception as e:
        logger.warning(f"{e} while splitting colors")
        traceback.print_exc()
    return st, new_pos


O_SYM = Symbols("NFO", SYMBOL, EXPIRY, DIFF)
O_API = get_api(BRKR, IS_LIVE)
ST = si.SuperTrend(SUPR["atr"], SUPR["multiplier"])
SMA_ = si.SMA(SMA_SETG["period"])


def get_historical_for_option(tkn, option_name):
    lastBusDay = pendulum.now()
    fromBusDay = lastBusDay.replace(
        hour=9, minute=15, second=0, microsecond=0
    ).subtract(days=7)
    resp = O_API.historical(
        "NFO", tkn, fromBusDay.timestamp(), lastBusDay.timestamp(), 15
    )
    if not resp:
        logger.error(
            f"Historical data is not available for {option_name}. Exiting")
        sys.exit()
    logger.info(f"Checking historical data for {option_name}")
    df = pd.DataFrame(resp).iloc[:100].iloc[::-1]
    df = df[["time", "intc"]]
    df["timestamp"] = (
        pd.to_datetime(
            df["time"], format="%d-%m-%Y %H:%M:%S").astype("int64") // 10**9
    )
    df.rename(columns={"intc": "close",
              "time": "timestamp_column"}, inplace=True)
    df["close"] = df["close"].astype("float")
    df["Symbol"] = option_name
    df["historical_count"] = len(df)
    return df


def run(dct_symtkns, option_details):
    df_ticks = pd.DataFrame()
    ival = 0
    while not is_time_past("15:20:00"):
        for option_name in option_details:
            if option_details[option_name].empty:
                option_details[option_name] = get_historical_for_option(
                    str(dct_symtkns[option_name]), option_name
                )
            df_ticks = option_details[option_name]
            r = RenkoWS(
                df_ticks["timestamp"].iat[0],
                df_ticks["close"].iat[0],
                brick_size=SETG[SYMBOL]["brick"],
            )
            for key, candle in df_ticks.iterrows():
                if key == 0:
                    continue
                r.add_prices(candle["timestamp"], candle["close"])
            if (0 + ival) >= len(df_ticks):
                continue

            ulying = get_ltp(O_API, str(dct_symtkns[option_name]))
            if ulying == 0:
                return

            df_ticks.loc[len(df_ticks)] = {
                "timestamp": dt.now().timestamp(),
                "Symbol": option_name,
                "close": ulying,
            }
            option_details[option_name] = df_ticks
            logger.info(
                f"Added one entry to {option_name}_df the total len now is {len(df_ticks)}"
            )
            logger.info(df_ticks.tail(5))
            r.add_prices(
                df_ticks["timestamp"].iat[(
                    0 + ival)], df_ticks["close"].iat[(0 + ival)]
            )
            df_normal = r.renko_animate("normal")
            # df_normal.to_csv(f"df_normal_{ival}.csv")
            for key, candle in df_normal.iterrows():
                st_dir, st = ST.update(candle)
                # add the st value to respective row
                # in the dataframe
                df_normal.loc[key, "st"] = st
                df_normal.loc[key, "st_dir"] = st_dir
                val = (candle["high"] + candle["low"] + candle["close"]) / 3
                df_normal.loc[key, "sma"] = SMA_.update(val)

            # get direction and split colors of supertrend
            df_normal, new_pos = split_colors(df_normal, option_name, df_ticks)
            # try:
            #     df_normal.to_csv("banknifty_v2_df_normal.csv")
            # except:
            #     pass

            # update positions if they are available
            if any(new_pos):
                logger.debug(f"found {new_pos=}")
            print("Positions \n", O_API.positions)
        ival += 1
    else:
        logger.info("Time to exit")
        SystemExit()


def main():
    O_SYM.get_exchange_token_map_finvasia()
    dct_symtkns = O_SYM.get_all_tokens_from_csv()
    atm = O_SYM.get_atm(get_ltp(O_API))
    ce_option, pe_option = (
        O_SYM.find_itm_option(atm, "C"),
        O_SYM.find_itm_option(atm, "P"),
    )
    while not is_time_past("09:30:00"):
        timer(1)
        atm = O_SYM.get_atm(get_ltp(O_API))
        print("atm is:", atm, "sleeping ..")
        ce_option, pe_option = (
            O_SYM.find_itm_option(atm, "C"),
            O_SYM.find_itm_option(atm, "P"),
        )
    else:
        option_details = {ce_option: pd.DataFrame(), pe_option: pd.DataFrame()}
        run(dct_symtkns, option_details)


main()
