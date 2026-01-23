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
import json

import yaml
try:
    from yaml import CSafeLoader as SafeLoader
except ImportError:
    from yaml import SafeLoader

import yaml.scanner
from yaml_runner import YamlRunner

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


class XTS():
    """
    XTS class for managing XTS configuration and running commands.

    Attributes:
        _xts_config (dict, optional): Parsed XTS configuration data. Defaults to None.
        _command_sections (dict): Dictionary of command sections extracted from configuration.
        _plugins (list): List of plugin classes providing additional commands.
        _used_args (list): List of command-line arguments used.
    """

    def __init__(self):
        """
        Initializes an XTS object.
        """
        self._xts_config = None
        self._command_sections = {}
        self._plugins = [XTSAllocatorClient]
        # self._used_args = []

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
    

    def _parse_first_arg(self):
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
                                             add_help=False)
        first_arg_parser.add_argument('--alias',
                                      action='store_true',
                                      help='Add/Remove or list aliases',
                                      dest='alias_option',
                                      default=False)
        args, remaining_args = first_arg_parser.parse_known_args(sys.argv[1:])

        if args.alias_option:
            xts_alias.run_alias_builtin(remaining_args)
            raise SystemExit(0)

        if not remaining_args:
            first_arg_parser.print_help()
            raise SystemExit(0)

        alias_name = remaining_args[0]
        resolved_xts_path = xts_alias.resolve_alias_to_xts_path(alias_name)
        
        if resolved_xts_path is None:
            error(
                f'Unknown alias "{alias_name}". '
                'Use "xts --alias --list" to see available aliases.'
            )
            raise SystemExit(1)

        # load xts config remove alias name from argv before parsing
        self.xts_config = resolved_xts_path

        return remaining_args[1:]

    def run(self):
        """Run the XTS app.

        Raises:
            SystemExit: Raised when unrecogised arguments are given.
        """
        args = self._parse_first_arg()
        
        if not args:
            info("Available commands:")
            choices = self._get_yaml_command_choices()
            if not choices:
                warning("No commands found in this .xts config.")
                raise SystemExit(0)

            for cmd, desc in choices:
                if desc:
                    info(f"  [bold]{cmd}[/bold] - {desc}")
                else:
                    info(f"  [bold]{cmd}[/bold]")
            raise SystemExit(0)

        try:
            yaml_runner = YamlRunner(
                self._command_sections,
                program='xts',
                hierarchical=True,
                fail_fast=True,
                parser_class=XTSArgumentParser
            )

            _, _, exit_code = yaml_runner.run(args)
            sys.exit(sorted(exit_code)[-1])

        except Exception as e:
            error(
                'An unrecognised command caused an error\n\n'
                f'Command Args: [{" ".join(args)}]\n\n'
                f'{str(e)}'
            )

def main():
    XTS().run()

if __name__ == "__main__":
    main()