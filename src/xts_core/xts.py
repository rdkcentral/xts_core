#!/usr/bin/env python3
#** *****************************************************************************
# *
# * If not stated otherwise in this file or this component's LICENSE file the
# * following copyright and licenses apply:
# *
# * Copyright 2024 RDK Management
# *
# * Licensed under the Apache License, Version 2.0 (the "License");
# * you may not use this file except in compliance with the License.
# * You may obtain a copy of the License at
# *
# *
# http://www.apache.org/licenses/LICENSE-2.0
# *
# * Unless required by applicable law or agreed to in writing, software
# * distributed under the License is distributed on an "AS IS" BASIS,
# * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# * See the License for the specific language governing permissions and
# * limitations under the License.
# *
#* ******************************************************************************

"""XTS command-line tool for executing commands from YAML configuration files.

This script provides a command-line interface (CLI) for running commands
defined within an XTS configuration file (`.xts` extension). It allows for:

* Parsing arguments from the command line.
* Processing the XTS configuration file, ensuring it's a valid YAML file.
* Executing the defined commands based on the configuration.

The script utilizes the `yaml_runner` module to handle configuration
parsing and command execution.
"""
import argparse
import os
import re
import sys

import yaml
try:
    from yaml import CSafeLoader as SafeLoader
except ImportError:
    from yaml import SafeLoader

import yaml.scanner
from yaml_runner import YamlRunner
import argparse_completion

try:
    from .plugins import XTSAllocatorClient
except ImportError:
    from xts_core.plugins import XTSAllocatorClient

try:
    from .utils import info, error, warning, is_url
except ImportError:
    from xts_core.utils import info, error, warning, is_url

try:
    from . import xts_alias
except ImportError:
    from xts_core import xts_alias

try:
    from .xts_arg_parser import XTSArgumentParser
except ImportError:
    from xts_core.xts_arg_parser import XTSArgumentParser

from xts_core.xts_rich_help_formatter import XTSRichHelpFormatter


class XTS():
    """
    XTS class for managing XTS configuration and running commands.

    Attributes:
        _xts_config (dict, optional): Parsed XTS configuration data. Defaults to None.
        _command_sections (dict): Dictionary of command sections extracted from configuration.
        _plugins (list): List of plugin classes providing additional commands.
    """

    def __init__(self):
        """
        Initializes an XTS object.
        """
        self._xts_config = None
        self._command_sections = {}
        self._plugins = [XTSAllocatorClient]

    @property
    def xts_config(self):
        """
        Returns a copy of the currently loaded XTS configuration.

        Returns:
            dict or None: Copy of the XTS configuration dictionary if loaded, else None.
        """
        if isinstance(self._xts_config,dict):
            return self._xts_config.copy()
        else:
            return self._xts_config

    @xts_config.setter
    def xts_config(self, config:str):
        """
        Sets the XTS configuration based on the provided file path.

        Validates the existence and extension of the provided configuration
        file. If valid, attempts to load the YAML data using the `yaml.load`
        function with `SafeLoader` for security. 

        Args:
            config (str): Path to the XTS configuration file.

        Raises:
            SystemExit: If file does not exist, cannot be read, or YAML parsing fails.
        """
        if os.path.exists(config) and re.search(r'.xts$',config):
            try:
                with open(config, 'r', encoding='utf-8') as config_stream:
                    self._xts_config = yaml.load(config_stream,SafeLoader)
                    self._command_sections = self._get_command_sections()
            except PermissionError:
                error(f'Could not read xts config: {config}')
            except yaml.scanner.ScannerError as e:
                error(f'The xts file is incorrectly formatted: {config}')
        else:
            error('xts config specified does not exist')    


    def _get_yaml_command_choices(self) -> list[tuple]:
        """
        Return only YAML-defined commands from the loaded xts config.
        (No plugin commands here.)
        """
        choices_with_desc = []
        if self._xts_config:
            for command, details in self._command_sections.items():
                description = details.get('description', '')
                choices_with_desc.append((command, description))
        return choices_with_desc

    def _get_command_sections(self) -> dict:
        """Extract command sections from loaded XTS configuration."""
        command_sections = {}

        def _is_command_section(subdict: dict) -> bool:
            for key, value in subdict.items():
                if key == 'command':
                    return True
                elif isinstance(value, dict) and _is_command_section(value):
                    return True
            return False
        
        if not isinstance(self._xts_config, dict):
            return command_sections

        for key, value in self._xts_config.items():
            if isinstance(value, dict) and _is_command_section(value):
                command_sections[key] = value

        return command_sections
    

    def _setup_first_parser(self):
        """
        Parse CLI arguments and set up argparse for all commands.
        The first argument must be either:
        - a built-in option starting with '--' (currently supported: --alias)
        - an alias name (resolved via ~/.xts/aliases.json to an .xts file path)
        Direct .xts file usage from cwd or as the first argument is not supported.

        Returns:
            list[str]: Remaining args starting with the command name, e.g. ["run", ...].
        """
        first_arg_parser = XTSArgumentParser(prog='xts',
                                             formatter_class=XTSRichHelpFormatter,
                                             add_help=False)
        first_arg_subparsers = first_arg_parser.add_subparsers(dest='alias_name',
                                                               metavar='')
        known_aliases = sorted(list(xts_alias.load_aliases()))
        if len(known_aliases) >= 1:
            first_arg_subparsers.add_parser('alias_name',
                                            aliases=known_aliases,
                                            help='Alias to run commands from.',
                                            add_help=False)

        alias_parser = first_arg_subparsers.add_parser('alias',
                                                        help='Manage aliases (add, list, remove)')
        xts_alias.setup_alias_parser(alias_parser)
        return first_arg_parser
    
    def _run_yaml_runner(self, alias:str, arguments:list[str]):
        resolved_xts_path = xts_alias.resolve_alias_to_xts_path(alias)
        # load xts config remove alias name from argv before parsing
        self.xts_config = resolved_xts_path
        try:
            yaml_runner = YamlRunner(
                self._command_sections,
                program=f'xts {alias}',
                hierarchical=True,
                fail_fast=True,
                parser_class=XTSArgumentParser
            )

            _, _, exit_code = yaml_runner.run(arguments)
            raise SystemExit(sorted(exit_code)[-1])
        except Exception as e:
                    error(
                        'An unrecognised command caused an error\n\n'
                        f'Command Args: [{" ".join(arguments)}]\n\n'
                        f'{str(e)}')
    
    def _run_completion(self, arg_parser:XTSArgumentParser):
        os.environ['_ARGPARSE_COMPLETE'] = os.getenv('_XTS_COMPLETE')
        completion = argparse_completion.get_completion(arg_parser)
        if 'alias_name' in completion:
            completion.remove('alias_name')
        if len(completion) == 0 and (comp_words:=(os.getenv('COMP_WORDS').split()))[1] in xts_alias.load_aliases().keys():
            os.environ['_YAML_RUNNER_COMPLETE'] = os.getenv('_XTS_COMPLETE')
            alias = comp_words[1]
            comp_words.remove('xts')
            comp_words.remove(alias)
            os.environ['COMP_WORDS'] = " ".join(comp_words)
            self._run_yaml_runner(alias, comp_words)
        else:
            print('\n'.join(completion))
        
    def run(self):
        """Run the XTS app.

        Raises:
            SystemExit: Raised when unrecogised arguments are given.
        """
        parser = self._setup_first_parser()
        if os.getenv('_XTS_COMPLETE'):
            self._run_completion(parser)
            raise SystemExit(0)
        if len(sys.argv) <= 1:
            parser.print_help()
            raise SystemExit(0)
        args, remaining_args = parser.parse_known_args()
        args = vars(args)
        alias_name = args.get('alias_name')
        match alias_name:
            case 'alias':
                alias_name_subparser = list(filter(lambda x: x.dest == 'alias_name',parser._actions))[0]
                alias_subparser = alias_name_subparser.choices.get('alias')
                xts_alias.run_alias_builtin(alias_subparser)
            case None|'alias_name':
                parser.print_help()
                raise SystemExit(0)
            case _:
                self._run_yaml_runner(alias_name, remaining_args)


def main():
    XTS().run()

if __name__ == "__main__":
    main()