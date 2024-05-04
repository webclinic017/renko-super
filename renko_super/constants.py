from toolkit.fileutils import Fileutils
from toolkit.utilities import Utilities
from toolkit.logger import Logger

FUTL = Fileutils()
DATA = "../data/"
LOG = DATA + "log.txt"
if FUTL.is_file_exists(LOG):
    print(f"log file found {LOG}")
logging = Logger(10, LOG)
DIRP = "../../"
SETG = FUTL.get_lst_fm_yml(DIRP + "renko_super.yml")
BRKR = SETG["finvasia"]
print(BRKR)
SUPR = SETG["supertrend"]
SMA_SETG = SETG.get("sma", {"period": 20})
UTIL = Utilities()
