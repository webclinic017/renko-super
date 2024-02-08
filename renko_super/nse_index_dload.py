
import requests
import pandas as pd
from constants import DATA, UTIL

symbols = ["NIFTY 50", "NIFTY BANK"]
NSE = "https://www.nseindia.com"
API = NSE + "/api"


def get_session() -> requests.Session:
    _user_agent = requests.get(
        "https://techfanetechnologies.github.io/latest-user-agent/user_agents.json"
    ).json()[-2]
    s = requests.Session()
    s.verify = True
    s.headers.update({"User-Agent": _user_agent})
    s.get(NSE, timeout=(3.05, 10))
    return s


def pretify():
    print("*" * 100)


def main():
    for symbol in symbols:
        session = get_session()
        pretify()
        filepath = f"{DATA}{symbol.replace(' ', '_')}.csv"
        print(f"preparing ... to download data for {symbol}")
        dat = session.get(
            f"{API}/chart-databyindex",
            params={"index": symbol},
            timeout=(3.05, 10),
        ).json()
        df = pd.DataFrame(dat["grapthData"], columns=[
            "timestamp", "close"])
        print(f"downloaded ... {len(df)} lines of data for {symbol}")

        df['timestamp_column'] = pd.to_datetime(df['timestamp'], unit='ms')
        start_time = pd.Timestamp('09:15:00')
        # Calculate the difference in minutes from the start time and round to the nearest 15-minute interval
        minute_diff = (df['timestamp_column'] -
                       start_time).dt.total_seconds() / 60
        rounded_minute_diff = 15 * (minute_diff // 15)
        df['rounded_timestamp'] = start_time + \
            pd.to_timedelta(rounded_minute_diff, unit='m')

        # Filter the DataFrame to select the first occurrence of each rounded interval
        filtered_df = df[df['rounded_timestamp'] >= start_time].groupby(
            df['rounded_timestamp'].dt.floor('5min')).first()

        # Reset index to make 'rounded_timestamp' a regular column
        filtered_df = filtered_df.reset_index(drop=True)
        print(filtered_df.head())
        print(filtered_df.tail())
        # drop unwanted columns
        df.drop(columns=['timestamp_column',
                'rounded_timestamp'], inplace=True)
        print(
            f"reduced ... {len(filtered_df)} into lines of data for {symbol}")
        filtered_df.to_csv(filepath, header=True, index=False)
        UTIL.slp_for(2)
        pretify()
        session.close()


main()
