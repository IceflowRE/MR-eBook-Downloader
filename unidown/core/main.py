"""
Entry point for the downloader.
"""

import sys
import traceback
from argparse import ArgumentParser
from pathlib import Path

import unidown.core.data.dynamic as dynamic_data
import unidown.core.data.static as static_data
from unidown.core import manager


def main():
    if sys.version_info[0] < 3 or sys.version_info[1] < 6:
        sys.exit('Only Python 3.6 or greater is supported. You are using:' + sys.version)

    parser = ArgumentParser(prog='UniversalDownloader', description='Universal Downloader.')
    parser.add_argument('-v', '--version', action='version', version=(static_data.NAME + ' ' + static_data.VERSION))

    parser.add_argument('-p', '--plugin', nargs='+', dest='plugins', required=True, type=str, metavar='name',
                        help='list of using plugins')
    parser.add_argument('-m', '--main', dest='main_dir', default=dynamic_data.MAIN_DIR, type=Path, metavar='path',
                        help='main directory where all files will be created (default: %(default)s)')
    parser.add_argument('-o', '--output', dest='logfile', default=dynamic_data.LOGFILE_PATH, type=Path, metavar='path',
                        help='log filepath relativ to the main dir (default: %(default)s)')
    parser.add_argument('-l', '--log', dest='log_level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                        default=dynamic_data.LOG_LEVEL, help='set the logging level (default: %(default)s)')

    args = parser.parse_args()
    try:
        manager.init(Path(args.main_dir), Path(args.logfile), args.log_level)
    except PermissionError:
        print('Cant create needed folders. Make sure you have write permissions.')
        sys.exit(1)
    except FileExistsError as ex:
        print(ex)
        sys.exit(1)
    except Exception as ex:
        print('Something went wrong: ' + traceback.format_exc(ex.__traceback__))
        sys.exit(1)
    manager.check_update()
    manager.run(args.plugins)
    manager.shutdown()
    sys.exit(0)
