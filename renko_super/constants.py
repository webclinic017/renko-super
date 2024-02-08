from toolkit.fileutils import Fileutils
from toolkit.utilities import Utilities
from toolkit.logger import Logger

logging = Logger(10)
DATA = "../data/"
DIRP = "../../"
FUTL = Fileutils()
SETG = FUTL.get_lst_fm_yml(DIRP + "renko_super.yml")
BRKR = SETG["finvasia"]
SUPR = SETG["supertrend"]
UTIL = Utilities()
