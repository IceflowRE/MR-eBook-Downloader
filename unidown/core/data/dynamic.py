"""
Dynamical variables, which will be initialized and can be changed while runtime.
"""
from pathlib import Path

# paths
MAIN_DIR = Path('./')
TEMP_DIR = MAIN_DIR.joinpath(Path('temp/'))
DOWNLOAD_DIR = MAIN_DIR.joinpath(Path('downloads/'))
SAVESTAT_DIR = MAIN_DIR.joinpath(Path('savestates/'))
LOGFILE_PATH = MAIN_DIR.joinpath(Path('UniDown.log'))

USING_CORES = 1
LOG_LEVEL = 'INFO'
DISABLE_TQDM = False


def init_dirs(main_dir: Path, logfilepath: Path):
    global MAIN_DIR, TEMP_DIR, DOWNLOAD_DIR, SAVESTAT_DIR, LOGFILE_PATH
    MAIN_DIR = main_dir
    TEMP_DIR = MAIN_DIR.joinpath(Path('temp/'))
    DOWNLOAD_DIR = MAIN_DIR.joinpath(Path('downloads/'))
    SAVESTAT_DIR = MAIN_DIR.joinpath(Path('savestates/'))
    LOGFILE_PATH = MAIN_DIR.joinpath(logfilepath)


def reset():
    global MAIN_DIR, TEMP_DIR, DOWNLOAD_DIR, SAVESTAT_DIR, LOGFILE_PATH, USING_CORES, LOG_LEVEL, DISABLE_TQDM
    MAIN_DIR = Path('./')
    TEMP_DIR = MAIN_DIR.joinpath(Path('temp/'))
    DOWNLOAD_DIR = MAIN_DIR.joinpath(Path('downloads/'))
    SAVESTAT_DIR = MAIN_DIR.joinpath(Path('savestates/'))
    LOGFILE_PATH = MAIN_DIR.joinpath(Path('UniDown.log'))

    USING_CORES = 1
    LOG_LEVEL = 'INFO'
    DISABLE_TQDM = False


def check_dirs():
    dirs = [MAIN_DIR, TEMP_DIR, DOWNLOAD_DIR, SAVESTAT_DIR]
    for directory in dirs:
        if directory.exists() and not directory.is_dir():
            raise FileExistsError(str(directory.resolve()) + " cannot be used as a directory.")
