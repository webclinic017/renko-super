from toolkit.fileutils import Fileutils
from toolkit.utilities import Utilities
from toolkit.logger import Logger

logging = Logger(10, "./renko_super.log")
DATA = "../data/"
DIRP = "../../"
FUTL = Fileutils()
SETG = FUTL.get_lst_fm_yml(DIRP + "renko_super.yml")
BRKR = SETG["finvasia"]
SUPR = SETG["supertrend"]
EMA_SETG = SETG.get("ema", {"period": 20})
UTIL = Utilities()
