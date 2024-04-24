from toolkit.fileutils import Fileutils
from toolkit.utilities import Utilities
from toolkit.logger import Logger

logging = Logger(10, "./renko_super.log")
DATA = "../data/"
DIRP = "../../"
FUTL = Fileutils()
SETG = FUTL.get_lst_fm_yml(DIRP + "renko_super.yml")
BRKR = SETG["finvasia"]
print(BRKR)
SUPR = SETG["supertrend"]
SMA_SETG = SETG.get("sma", {"period": 20})
UTIL = Utilities()
