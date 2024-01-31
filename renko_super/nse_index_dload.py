
import requests
import pandas as pd
from constants import DATA, FUTL
import pendulum as pdlm

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


def main():
    session = get_session()
    for symbol in symbols:
        filepath = f"{DATA}{symbol.replace(' ', '_')}.csv"
        dat = session.get(
            f"{API}/chart-databyindex",
            params={"index": symbol},
            timeout=(3.05, 10),
        ).json()
        df = pd.DataFrame(dat["grapthData"], columns=[
            "timestamp", "close"])
        df.to_csv(filepath, header=True, index=False)


main()
