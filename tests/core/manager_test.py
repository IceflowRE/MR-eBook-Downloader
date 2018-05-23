import unittest
from pathlib import Path

import unidown.dynamic_data as dynamic_data
from unidown.core import manager


class ManagerTest(unittest.TestCase):
    def test_init(self):
        for path in [Path('./tmp'), Path('./tmp2/tmp')]:
            manager.init(path, Path('UniDown.log'), dynamic_data.LOG_LEVEL)
            with self.subTest(path=str(path), logfile='UniDown.log', loglevel=dynamic_data.LOG_LEVEL):
                self.assertTrue(path.joinpath('downloads').exists())
                self.assertTrue(path.joinpath('savestates').exists())
                self.assertTrue(path.joinpath('temp').exists())
                self.assertTrue(path.joinpath('UniDown.log').is_file())
