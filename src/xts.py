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

import os
import re
import sys

import rich
import yaml
try:
    from yaml import CSafeLoader as SafeLoader
except ImportError:
    from yaml import SafeLoader

from yaml_runner import YamlRunner, add_choices_to_help

class XTS(YamlRunner):
    """
    XTS class for managing XTS configuration and running commands.

    Inherits from the `YamlRunner` class to provide a framework for
    parsing arguments, processing configuration, and executing commands.

    Attributes:
        _xts_config (dict, optional): The internal dictionary containing the
            parsed XTS configuration data. Defaults to None.
    """


    def __init__(self):
        """
        Initializes an XTS object.
        """
        super().__init__(program='xts')
        self._xts_config = None

    @property
    def xts_config(self):
        """Returns a copy of the currently loaded XTS configuration."""
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
            except PermissionError:
                error(f'Could not read xts config: [{config}]')
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
        if len(sys.argv) > 1:
            if re.search(r'.xts$',sys.argv[1]):
                self.xts_config = sys.argv[1]
                # self.program += f' {sys.argv[1]}'
                self._used_args.append(sys.argv[1])
                sys.argv.pop(1)
        if self.xts_config is None:
            self._find_xts_config()
        parser = self.new_subparser(name='_parse_first_arg')
        parser.add_argument('--help','-h',
                            action='store_true',
                            help='Show the help information',
                            default=False)
        parser.add_argument('command',
                            action='store',
                            help='The command to run',
                            choices=list(self.xts_config.keys()),
                            default=None,
                            metavar='COMMAND')
        help_msg = parser.format_help()
        help_msg = add_choices_to_help(help_msg, 'COMMAND', list(self.xts_config.keys()))
        parser.usage = help_msg
        parsed_args, remaining = parser.parse_known_args()
        self.config = {parsed_args.command : self._xts_config.get(parsed_args.command)}
        # Now the command is known we can run a plugin an interrupt the run sequence
        self._run_plugins(parsed_args.command)
        self._used_args.append(parsed_args.command)
        if parsed_args.help:
            remaining.append('--help')
        # If first argument isn't a whole section but just a command
        # add the argument back into the argument list
        if self.config[parsed_args.command].get('command'):
            remaining.append(parsed_args.command)
        return remaining

    def _find_xts_config(self):
        """
        Searches for an XTS configuration file in the current directory.

        Raises:
            SystemExit: If no XTS configuration file is found.
        """
        files = os.listdir(os.getcwd())
        xts_configs = []
        for filename in files:
            regex = re.search(r'.xts$',filename)
            if regex:
                xts_configs.append(filename)
        if len(xts_configs) > 1:
            self._user_select_config(xts_configs)
        elif len(xts_configs) < 1:
            error('no config found')
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
        info('Multiple xts file found in the current directory')
        print('Please run one of the following commands to choose the file to use\n')
        for filename in choices:
            print(f'\txts {filename} ...')
        raise SystemExit(2)

    def _run_plugins(self,command):
        """
        Placeholder for future plugin support.

        This method is currently empty (`pass`) but serves as a placeholder for
        future implementation of plugin functionality to extend the XTS tool.

        Args:
            command (str): The name of the command being executed.
        """
        # TODO: Add plugin support to xts
        pass

    def run(self):
        """
        Runs the XTS script with the parsed configuration and arguments.

        Returns:
            Returns a tuple containing three lists: `stdout_list`, `stderr_list`, and `exit_code_list`.
                Each list contains the respective outputs (stdout, stderr,
                and exit code) of running the command(s) specified in the `self.commands` attribute..
        """
        unparsed_args = self._parse_first_arg()
        return super().run(config=self.config, args=unparsed_args)


def info(info_message):
    """
    Prints a Yellow informational message.

    Args:
        info_message (str): The informational message to be printed.
    """
    rich.print(f'[yellow]{info_message}[/yellow]')

def error(error_message):
    """
    Prints a Red error message and exits with exit code 1.

    Args:
        error_message (str): The error message to be printed.

    Raises:
        SystemExit: Exits the program due to the error
    """
    rich.print(f'[red][bold]ERROR:[/bold] {error_message}[/red]')
    raise SystemExit(1)

if __name__ == "__main__":
    XTS().run()
