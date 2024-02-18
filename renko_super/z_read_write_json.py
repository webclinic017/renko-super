from constants import DATA, FUTL
from pprint import pprint
import json

SYMBOL = "BANKNIFTY"
DATA += SYMBOL + "/"
F_POS = DATA + "positions.json"

dct = dict(symbol="", quantity=0, entry_price=0, urmtom=0, rpnl=0)
str_dct = json.dumps(dct)
FUTL.write_file(F_POS, str_dct)
jsn = FUTL.read_file(F_POS)
pprint(jsn)
