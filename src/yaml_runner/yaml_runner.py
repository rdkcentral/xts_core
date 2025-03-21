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

import argparse
import io
import subprocess
import re
import sys
import threading

import yaml
try:
    from yaml import CSafeLoader as SafeLoader
except ImportError:
    from yaml import SafeLoader

class YamlRunner():
    """YamlRunner class for executing commands from a YAML configuration file.

    This class provides a framework for running commands defined within a YAML
    configuration file. It allows for parsing arguments from the command line,
    processing the YAML configuration, and executing the defined commands.

    Attributes:
        _arg_parser (argparse.ArgumentParser): The main argument parser for the script.
        _command_dict (dict, optional): The dictionary containing the configuration for the
            currently selected command. Defaults to None.
        _config (dict, optional): The parsed YAML configuration data. Defaults to None.
        _external_args (list): A list containing all arguments passed to the script from the
            command line.
        _remaining_args (list, optional): A list containing arguments that haven't been used
            by previous parsers. Defaults to None.
        _subparsers (argparse._SubParsersAction): A container for creating subparsers for
            different commands.
        _program (str): The name of the program as specified when creating the YamlRunner object.
    """

    def __init__(self, program:str='', config:dict|io.IOBase|str=None):
        """Initiate a YamlRunner object

        Args:
            program (str, optional): Program name. Defaults to None
            config (dict | io.IOBase | str, optional): Yaml connfiguration of commands that can be run.
                Defaults to None. 
                If None, config is expected to be passed in from command line with `--config` option.
        """
        self._arg_parser = None
        self._command_dict = None
        self.commands = None
        self._config = None
        self._external_args = []
        self._remaining_args = None
        self._subparsers = None
        self._program = program
        self._used_args = [self._program]
        self._set_config(config)


    @property
    def config(self):
        """The config currently in use by the YamlRunner"""
        return self._config.copy()

    @config.setter
    def config(self,config):
        self._set_config(config)

    def new_subparser(self, name:str, help:str=None) -> argparse.ArgumentParser:
        """
        Create a new subparser with an optional help message.
        
        Args:
            help (str): Provide a brief description or usage information for the subparser being created. 
        
        Returns:
            An argparse.ArgumentParser instance.
        """
        program = self._get_used_args_string()
        subparser = self._subparsers.add_parser(name=name, add_help=False, help=help, prog=program)
        return subparser

    def _set_config(self, config:dict|io.IOBase|str|None) -> None:
        """Set up the config based on input type (dictionary, file, string)
        and then sets up parsers accordingly.
        
        Args:
            config (dict|io.IOBase|str|None): Config file, path or dictionary.
                                                If None, config remains unset.
        """
        if isinstance(config,str):
            with open(config,'r',encoding='utf-8') as f:
                self._config = yaml.load(f,SafeLoader)
        elif isinstance(config,io.IOBase):
            config.seek(0)
            self._config = yaml.load(config,SafeLoader)
        elif isinstance(config,dict):
            self._config = config
        elif config is None:
            self._config = None
        else:
            raise TypeError(f'config argument must of type IO, str or dict. Got type: [{type(config)}]')
        # Now the config is setup, the parser can be setup
        # If the config is changed the parser need to be setup again
        self._set_parsers()

    def _set_parsers(self):
        """Setup the parent argument parser and enable subparsers"""
        self._arg_parser = argparse.ArgumentParser(prog=self._program)
        self._subparsers = self._arg_parser.add_subparsers()

    def _set_initial_args(self) -> argparse.ArgumentParser:
        """
        Sets up and returns the initial argument parser with default arguments set.
        
        Returns:
            The initial `argparse.ArgumentParser` object.
        """
        parser = self.new_subparser(name='initial_args')
        # If config isn't already setup, expect it to be passed in from the command line.
        if self._config is None:
            parser.add_argument('-c', '--config',
                                        help='Full path to yaml config file',
                                        dest='config_path',
                                        action='store',
                                        metavar='YAML_CONFIG',
                                        required=True)
        parser.add_argument('-h', '--help',
                                    help='Show information about the command',
                                    dest='help',
                                    action='store_true',
                                    default=False
                                    )
        return parser

    def _get_pre_config_args(self):
        """
        Parses arguments passed to the script before the yaml has been parsed.
        """
        parser = self._set_initial_args()
        default_args, self._remaining_args = parser.parse_known_args(self._external_args)
        if self._config is None:
            self._set_config(default_args.config_path)
        if default_args.help and not self._config:
            parser.print_help()
            raise SystemExit(0)
        elif default_args.help:
            self._set_help_arg()

    def _get_command_sections(self, parsed_config: dict) -> list:
        """
        Recursive function to extract the command sections from a dictionary.
        
        Args:
          parsed_config (dict): Dictionary containing command configiguration data.
        
        Returns:
          A list of dictionaries containing command sections from the parsed configuration. Each
        dictionary includes the 'name' key with the corresponding key from the parsed configuration.
        """
        command_dicts = []
        for key, value in parsed_config.items():
            if isinstance(value,dict):
                if value.get('command',None):
                    value.update({'name':key})
                    command_dicts.append(value)
                else:
                    command_dicts += self._get_command_sections(value)
        return command_dicts

    def _get_used_args_string(self) -> str:
        """
        Retrieve a string of used arguments by removing unparsed arguments from a list of
        all external arguments.
        
        Returns:
            A string that contains a space separated list of all the arguments that have been used.
            If there are no used arguments, it will return `None`.
        """
        arg_string = None
        all_args = self._external_args.copy()
        if isinstance(self._remaining_args,list):
            for unparsed_arg in self._remaining_args:
                all_args.remove(unparsed_arg)
        difference = set(all_args).difference(set(self._used_args))
        self._used_args += list(difference)
        arg_string = ' '.join(self._used_args)
        return arg_string

    def _process_commands(self):
        """
        Sets up and runs argument parser with the commands found in the config.
        Sets self._command_dict with the corresponding dictionary for the command supplied
        
        Raises:
            SystemExit: If the user has not supplied a valid command or has supplied the option for help,
              prints the help message diplaying the commands available and descriptions for them if available.
        """
        commands = None
        command_dicts = self._get_command_sections(self._config)
        subparser = self.new_subparser(name='process_commands',help='Commands from config')
        command_choice_names = [command_dict.get('name') for command_dict in command_dicts]
        subparser.add_argument('command',
                                help='These are available commands found in the config',
                                choices=command_choice_names,
                                nargs='?',
                                default=None,
                                metavar='COMMAND'
                                )
        subparser.add_argument('-h', '--help', '--h',
                                action='store_true',
                                dest='help',
                                help='Show information about the command',
                                default=False)
        commands, self._remaining_args = subparser.parse_known_args(self._remaining_args)
        if commands.command is None:
            help_message = subparser.format_help()
            choice_info = []
            for command_dict in command_dicts:
                if command_dict.get('description'):
                    choice_info.append((command_dict.get('name'),command_dict.get('description')))
                else:
                    choice_info.append(command_dict.get('name'))
            help_message = add_choices_to_help(help_message,'COMMAND',choice_info)
            print(help_message)
            raise SystemExit(0)
        if commands.help:
            self._set_help_arg()
        self._command_dict = list(filter(lambda x: x.get('name') == commands.command, command_dicts))[0]

    def _process_command_params(self, passthrough:bool=False, params:dict=None):
        """
        Sets up and runs the argument parser for the selected command.
        Sets the self.commands attribute to the command with parameters substituted into it.

        Raises:
            SystemExit: If the help option is passed with the command.
                        Prints the commands help message before exiting.
        """
        subparser = self.new_subparser('command_params')
        subparser.add_argument('-h', '--help', '--h',
                                help='Show this information',
                                action='store_true',
                                dest='help')
        if passthrough:
            subparser.add_argument('passthrough',
                                nargs='*',
                                metavar='PASSTHROUGH',
                                help='All arguments here will be passed into the command')
        # TODO: Implement parameter substitution from parameters in config.
        if params:
            pass
        command_params, _ = subparser.parse_known_args(self._remaining_args)
        for index, command in enumerate(self.commands):
            if '$@' in command:
                self.commands[index] = command.replace('$@', ' '.join(self._remaining_args))
        if command_params.help:
            subparser.print_help()
            raise SystemExit(0)

    def _process_command_config(self):
        """
        This function processes the selected commands configuration,
        setting the options of the commands parameters.
        """
        passthrough=False
        command = self._command_dict.get('command')
        if isinstance(command,list):
            self.commands = command
        else:
            self.commands = [command]
        if filter(lambda x: '$@' in x, self.commands):
            passthrough=True
        self._process_command_params(passthrough=passthrough, params=self._command_dict.get('params',None))


    def _run_command(self,command) -> tuple:
        """Runs a command in the shell, captures both stdout and stderr, 
        prints them in real-time, and returns them.

        Args:
            command: A list containing the command and its arguments.

        Returns:
            A tuple containing captured stdout (bytes) and stderr (bytes).
        """
        stdout_result = []
        stderr_result = []
        with subprocess.Popen(command,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                text=True,
                                shell=True) as proc:
            stdout_thread = threading.Thread(target=_read_stream,
                                             args=(proc.stdout, 'stdout',stdout_result))
            stderr_thread = threading.Thread(target=_read_stream,
                                             args=(proc.stderr, 'stderr', stderr_result))
            stdout_thread.start()
            stderr_thread.start()
            # Wait for the process to finish
            return_code = proc.wait()
            # Ensure threads finish reading and collect data
            stdout_thread.join()
            stdout = stdout_result[0]
            stderr_thread.join()
            stderr = stderr_result[0]
        return stdout, stderr, return_code

    def _run_commands(self) -> tuple:
        """
        Runs a list of commands in the self.commands attribute and returns the stdout, stderr, and exit
        codes for each command.
        
        Returns:
            Returns a tuple containing three lists: `stdout_list`, `stderr_list`, and `exit_code_list`.
              Each list contains the respective outputs (stdout, stderr,
              and exit code) of running the command(s) specified in the `self.commands` attribute.
        """
        stdout_list = []
        stderr_list = []
        exit_code_list = []
        for command in self.commands:
            stdout, stderr, exit_code = self._run_command(command)
            stdout_list.append(stdout)
            stderr_list.append(stderr)
            exit_code_list.append(exit_code)
        return stdout_list, stderr_list, exit_code_list


    def run(self, config:dict|io.IOBase|str=None, args:list=None) -> tuple:
        """
        This function runs a script with specified configuration and arguments, processing command line
        arguments and executing commands.
        
        Args:
            config (dict|io.IOBase|str): Yaml connfiguration of commands that can be run. Defaults to None.
                If None, config is expected to be passed in from command line with `--config` option.
            args (list): The arguments passed to the script. Defaults to None. 
                If None, external args are processed and used instead.
        
        Returns:
            Returns a tuple containing three lists: `stdout_list`, `stderr_list`, and `exit_code_list`.
              Each list contains the respective outputs (stdout, stderr,
              and exit code) of running the command(s) specified in the `self.commands` attribute.
        """
        if config:
            self._set_config(config)
        if args:
            self._external_args = args
        else:
            # Store a copy of the arguments passed to the script,
            # minus the actual script call
            self._external_args = sys.argv[1:].copy()
        # Process the args from the command line unrelated to the config
        # potentially processing the --config arg
        self._remaining_args = None
        self._get_pre_config_args()
        self._process_commands()
        self._process_command_config()
        return self._run_commands()


    def _set_help_arg(self):
        """Add the same "help" argument into the remaining args so it can be parsed by
        the next subparser.

        Raises:
            RuntimeError: If the function is called but the "help" argument wasn't set by the user.
        """
        if '--help' in self._external_args:
            self._remaining_args.append('--help')
        elif '-h' in self._external_args:
            self._remaining_args.append('-h')
        elif '--h' in self._external_args:
            self._remaining_args.append('--h')
        else:
            raise RuntimeError('Help is being set but was not an argument')

def add_choices_to_help(help_string:str, command_metavar:str, choices:list) -> str:
    """Adds the choices to the help string under the specified command with the corresponding metavar.
    
    Args:
        help_string (str): The help text for a command-line tool.
        command_metavar (str): The metavar for a command in the help string,
            which need choices to be added.
        choices (list): The list of choices.
    
    Returns:
        The `help_string` with the choices added under the specified command metavar.

    Raises:
        ValueError: If help string doesn't match the format expected (argparse's default).
        IndexError: If command_metavar isn't found in help_string.
    """
    help_lines = help_string.split('\n')
    command_index = None
    # Iterate through the lines to find the index of the line with the command metavar
    for count,line in enumerate(help_lines):
        find_command_help_line = re.match(fr'^[\s]+{command_metavar}.*', line)
        if find_command_help_line:
            command_index = count
            break
    # If an index is found it can be used
    if isinstance(command_index,int):
        command_help = help_lines[command_index]
        # Use a regex to find where the description of the command metavar starts
        match = re.match(fr'[\s]+{command_metavar}[\s]+',command_help)
        if match:
            # Find out how far we need to indent in to match the description section
            start_index, indent_index =  match.span()
            indent = ' ' * (indent_index)
            help_lines.insert(command_index+1,indent+'Choices:')
            command_index+=1
            indent+='  '
            for choice in choices:
                if isinstance(choice,tuple):
                    help_lines.insert(command_index+1,indent+choice[0]+' - '+choice[1])
                    command_index+=1
                else:
                    help_lines.insert(command_index+1,indent+choice)
                    command_index+=1
        else:
            # The regexs in this function only work on the default
            # format for argparse help strings
            raise ValueError('help_string expected in standard format')
    else:
        raise IndexError('command_metavar not found in help string')
    return '\n'.join(help_lines)

def _read_stream(stream:io.IOBase, target:str, result_list:list):
    """Read data from a stream and writes it to either stdout or stderr whilst also
    capturing the data.
    
    Args:
        stream (io.IOBase): Stream object from which data will be read.
        target (str): Where the output from the stream should be directed. Either 'stdout' or 'stderr'
        result_list (list): The list that will store the data read from the stream. 
            Each chunk of data read from the stream will be appended to this list.
    """
    data = ''
    if target == 'stdout':
        output = sys.stdout
    elif target == 'stderr':
        output = sys.stderr

    while True:
        chunk = stream.readline()
        if chunk == '':
            break
        data += chunk
        output.write(chunk)
        output.flush()
    result_list.append(data)
