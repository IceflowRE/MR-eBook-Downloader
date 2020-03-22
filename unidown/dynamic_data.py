"""
Dynamical variables, which will be initialized and can be changed while runtime or needs third party libraries (like pathlib.Path).
"""
from pathlib import Path

from packaging.version import Version

# paths
#: main path
MAIN_DIR = Path('./')
#: temporary main path, here are the sub folders for every plugin
TEMP_DIR = MAIN_DIR.joinpath(Path('temp/'))
#: download main path, here are the sub folders for every plugin
DOWNLOAD_DIR = MAIN_DIR.joinpath(Path('downloads/'))
#: savestates main path, here are the sub folders for every plugin
SAVESTATE_DIR = MAIN_DIR.joinpath(Path('savestates/'))
#: log file of the program
LOG_FILE = MAIN_DIR.joinpath(Path('UniDown.log'))

#: available plugins which are found at starting the program, name -> EntryPoint
AVAIL_PLUGINS = {}

#: how many core should be used
USING_CORES = 1
#: log level
LOG_LEVEL = 'INFO'
#: if the console progress bar is disabled
DISABLE_TQDM = False

#: current savestate version which will be used **Do not edit**
SAVESTATE_VERSION = Version('1')


# ===========================


def init_dirs(main_dir: Path, log_file: Path = None):
    """
    Initialize the main directories.

    :param main_dir: main directory
    :param log_file: log file
    """
    global MAIN_DIR, TEMP_DIR, DOWNLOAD_DIR, SAVESTATE_DIR, LOG_FILE
    MAIN_DIR = main_dir
    TEMP_DIR = MAIN_DIR.joinpath(Path('temp/'))
    DOWNLOAD_DIR = MAIN_DIR.joinpath(Path('downloads/'))
    SAVESTATE_DIR = MAIN_DIR.joinpath(Path('savestates/'))
    if log_file is None:
        LOG_FILE = MAIN_DIR.joinpath(Path('UniDown.log'))
    else:
        LOG_FILE = log_file


def reset():
    """
    Reset all dynamic variables to the default values.
    """
    global MAIN_DIR, TEMP_DIR, DOWNLOAD_DIR, SAVESTATE_DIR, LOG_FILE, USING_CORES, LOG_LEVEL, DISABLE_TQDM, \
        SAVESTATE_VERSION
    init_dirs(Path('./'))

    USING_CORES = 1
    LOG_LEVEL = 'INFO'
    DISABLE_TQDM = False

    SAVESTATE_VERSION = Version('1')


def check_dirs():
    """
    Check the directories if they exist.

    :raises FileExistsError: if a file exists but is not a directory
    """
    dirs = [MAIN_DIR, TEMP_DIR, DOWNLOAD_DIR, SAVESTATE_DIR]
    for directory in dirs:
        if directory.exists() and not directory.is_dir():
            raise FileExistsError(str(directory.resolve()) + " cannot be used as a directory.")
