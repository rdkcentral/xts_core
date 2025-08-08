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
try:
    from .plugins import XTSAllocatorClient
except ImportError:
    from xts_core.plugins import XTSAllocatorClient
try:
    from .utils import info, error, warning
except:
    from xts_core.utils import info, error, warning

from plugins import XTSAllocatorClient
import xts_loader

class XTS():
    """
    XTS class for managing XTS configuration and running commands.

    Attributes:
        _xts_config (dict, optional): The internal dictionary containing the
                                      parsed XTS configuration data. Defaults to None.
        _plugins (list): Plugin classes from imported plugins.
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
        """Returns a copy of the currently loaded XTS configuration."""
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
        
        Raises:
            SystemExit: if the file cannot be read or other errors during loading.
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

    def _parse_first_arg(self):
        """
        Parses the first argument provided to xts.

        Checks if an argument is provided. If it is a valid XTS configuration
        file path, sets the `xts_config` attribute. Otherwise, attempts to
        find a configuration file in the current directory.
        With the config in place, updates internal arguments and program name.

        Returns:
         list : remaining arguments after parsing the first argument.
        """
        # if len(sys.argv) > 1:
        #     if re.search(r'.xts$',sys.argv[1]):
        #         self.xts_config = sys.argv[1]
        #         self._used_args.append(sys.argv[1])
        #         sys.argv.pop(1)
        
        if len(sys.argv) > 1:
            arg = sys.argv[1]
            if arg in ["alias", "list-alias", "remove-alias"]:
                self._handle_alias_commands()
                sys.exit(0)

            # Accept alias, URL, or local .xts
            try:
                resolved_path = xts_loader.resolve_alias_or_url(arg)
                # self._xts_config
                self.xts_config = resolved_path
                self._used_args.append(arg)
                sys.argv.pop(1)
            except Exception as e:
                error(f"Could not resolve XTS config from '{arg}': {e}")

        if self.xts_config is None:
            self._find_xts_config()
        parser = argparse.ArgumentParser(prog='xts')
        subparsers = parser.add_subparsers(dest='command',required=True)
        for command, description in self._get_command_choices():
            subparsers.add_parser(command,
                                  help=description,
                                  add_help=False)
        # Parsing here will raise SystemExit() early if an invalid command is used or
        # if --help is called with no other arguments.
        parsed_args, remaining =  parser.parse_known_args()
        command_args = [parsed_args.command] + remaining
        return command_args
        

    def _handle_alias_commands(self):
        args = sys.argv[1:]
        if args[0] == "alias" and len(args) == 3:
            xts_loader.add_alias(args[1], args[2])
            print(f"Alias '{args[1]}' -> '{args[2]}' added.")
        elif args[0] == "list-alias":
            aliases = xts_loader.list_aliases()
            for k, v in aliases.items():
                print(f"{k} -> {v}")
        elif args[0] == "remove-alias" and len(args) == 2:
            xts_loader.remove_alias(args[1])
            print(f"Alias '{args[1]}' removed.")
        else:
            print("Usage:")
            print("  xts alias <name> <path_or_url>")
            print("  xts list-alias")
            print("  xts remove-alias <name>")
    
    def _find_xts_config(self):
        """
        Searches for an XTS configuration file in the current directory.

        Raises:
            SystemExit: If no XTS configuration file is found.
        """
        files = next(os.walk(os.getcwd()))[2]
        xts_configs = []
        for filename in files:
            regex = re.search(r'.xts$',filename)
            if regex:
                xts_configs.append(filename)
        if len(xts_configs) > 1:
            self._user_select_config(xts_configs)
        elif len(xts_configs) < 1:
            if len(self._plugins) < 1:
                error('No config found.')
            else:
                warning('No config found. Continuing only with commands from plugins.')
        else:
            self.xts_config = xts_configs[0]

    def _user_select_config(self, choices):
        """
        Print out list commands with found xts configs to run xts with each.
        Exits after running to allow user to do so.

        Args:
            choices (list): A list of filenames for the available XTS configuration files.

        Raises:
            SystemExit: Exits with 2 exit code to allow user to re-run the script. 
        """
        warning('Multiple xts file found in the current directory')
        print('Please run one of the following commands to choose the file to use\n')
        for filename in choices:
            print(f'\txts {filename} ...')
        raise SystemExit(2)

    def _get_command_choices(self) -> list[tuple]:
        """
        Retrieves available command choices from the XTS configuration and plugins.
        It extracts command names from the loaded XTS configuration file.
        If a command has a description, it stores it as a tuple (command, description).
        Additionally, it collects commands provided by loaded plugins.

        Returns:
            list[tuple]: A list of available commands, with descriptions as tuples (command, description) where applicable.
        """
        choices_with_desc = []

        if self._xts_config:
            for command, details in self._command_sections.items():
                description = details.get('description', '')
                choices_with_desc.append((command, description))  #store as tuple (command, description)
        #additional commands provided by plugins
        for plugin in self._plugins:
            choices_with_desc.extend(plugin().provided_args)
        return choices_with_desc

    def _get_command_sections(self) -> dict:
        """
        Gets the sections with commands in them from the config.

        Returns:
            dict: Dictionary containing only keys that have commands in them.
                    The commands could be nested in further dictionaries.
        """
        command_sections = {}
        def _is_command_section(subdict: dict) -> bool:
            """Check dictionary and nested dictionarys for "command" key.

            Args:
                subdict (dict): Nested dictionary to check.

            Returns:
                bool: True if command key found. False otherwise.
            """
            result = False
            for key, value in subdict.items():
                if key == 'command':
                    result = True
                    break
                elif isinstance(value, dict):
                    result = _is_command_section(value)
            return result
        for key, value in self._xts_config.items():
            if isinstance(value,dict):
                if _is_command_section(value):
                    command_sections.update({key:self._xts_config.get(key)})
        return command_sections

    def run(self):
        """Run the XTS app.

        Raises:
            SystemExit: Raised when unrecogised arguments are given.
        """
        args = self._parse_first_arg()
        if plugins := list(filter(lambda x: args[0] in x().provided_positionals,self._plugins)):
            for plugin in plugins:
                plugin().run(args)
        else:
            try:
                yaml_runner = YamlRunner(self._command_sections,
                        program='xts',
                        hierarchical=True,
                        fail_fast=True)
                _,_,exit_code = yaml_runner.run(args)
                sys.exit(sorted(exit_code)[-1])
            except Exception as e:
                # This code should be unreachable, but is handled just in case.
                error('An unrecognised command has caused and error\n\n'+
                      f'Command Args: [{" ".join(args)}]\n\n'+
                      e)

def main():
    XTS().run()

if __name__ == "__main__":
    main()
