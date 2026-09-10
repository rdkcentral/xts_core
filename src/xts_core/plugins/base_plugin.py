#!/usr/bin/env python3

from abc import ABC,abstractmethod
import argparse

import pathlib
import sys
sys.path.append(pathlib.Path(__file__).parent.joinpath('..'))
try:
    import xts_core.utils as plugin_utils
except:
    import utils as plugin_utils

try:
    from xts_core.xts_arg_parser import XTSArgumentParser
except ImportError:
    from xts_arg_parser import XTSArgumentParser

class BaseXTSPlugin(ABC):
    config_dir = pathlib.Path.home().joinpath('.xts')

    def __init__(self):
        self._prog_parser = XTSArgumentParser(prog='xts')
        self._subparsers = self._prog_parser.add_subparsers(dest='command')

    @abstractmethod
    def run(self,args: list):
        """Run the plugin.

        Args:
            args (list): Command-line arguments for the plugin.
        """
        pass
