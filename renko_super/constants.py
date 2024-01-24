from toolkit.fileutils import Fileutils
from toolkit.logger import Logger

logging = Logger(10)
DATA = "../data/"
DIRP = "../../"
FUTL = Fileutils()
CNFG = FUTL.get_lst_fm_yml(DIRP + "renko_super.yml")
BRKR = CNFG["finvasia"]
