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
from rich.console import Console

# Note: XTSAllocatorClient plugin removed in favor of centrally-managed
# .xts files from allocator servers. Use aliases instead:
#   xts alias add allocator http://server:5000/xts_allocator.xts

try:
    from .utils import info, error, warning, success, is_url
except:
    from xts_core.utils import info, error, warning, success, is_url

try:
    from . import xts_alias
except:
    from xts_core import xts_alias


class RichHelpFormatter(argparse.RawTextHelpFormatter):
    """Custom argparse formatter that adds rich color markup to help text."""
    
    def __init__(self, prog):
        super().__init__(prog, max_help_position=40, width=100)
    
    def _format_usage(self, usage, actions, groups, prefix):
        """Add color to usage line."""
        usage = super()._format_usage(usage, actions, groups, prefix)
        return f"[bold cyan]{usage}[/bold cyan]"
    
    def _format_action(self, action):
        """Add color to action items (commands and options)."""
        result = super()._format_action(action)
        if action.option_strings:
            # Color option flags like -h, --help
            for opt in action.option_strings:
                result = result.replace(opt, f"[yellow]{opt}[/yellow]")
        elif action.dest != 'help' and hasattr(action, 'choices') and action.choices:
            # Color subcommand names
            for choice in action.choices:
                result = result.replace(f"  {choice}", f"  [bold green]{choice}[/bold green]")
        return result
    
    def format_help(self):
        """Override to add section header colors."""
        help_text = super().format_help()
        # Color section headers
        help_text = help_text.replace('positional arguments:', '[bold yellow]positional arguments:[/bold yellow]')
        help_text = help_text.replace('options:', '[bold yellow]options:[/bold yellow]')
        help_text = help_text.replace('optional arguments:', '[bold yellow]optional arguments:[/bold yellow]')
        return help_text


class RichArgumentParser(argparse.ArgumentParser):
    """Custom ArgumentParser that uses rich to print help with colors."""
    
    def __init__(self, *args, **kwargs):
        if 'formatter_class' not in kwargs:
            kwargs['formatter_class'] = RichHelpFormatter
        super().__init__(*args, **kwargs)
        self.console = Console()
        self._command_list = []  # Store commands for nice display
    
    def print_help(self, file=None):
        """Override to use rich.print for colored output."""
        self.console.print(self.format_help())
    
    def set_command_list(self, commands):
        """Store the list of available commands for better error messages."""
        self._command_list = commands
    
    def set_alias_name(self, alias_name):
        """Store the alias name for display in error messages."""
        self._alias_name = alias_name
    
    def error(self, message):
        """Override to use rich for error messages and show nice command list."""
        # Check if this is a missing command error
        if 'required: command' in message and self._command_list:
            console = Console()
            if hasattr(self, '_alias_name'):
                console.print(f"\n[bold cyan]{self._alias_name}[/bold cyan] [dim]commands:[/dim]")
            else:
                console.print("\n[bold yellow]Available commands:[/bold yellow]")
            for cmd, desc in self._command_list:
                if cmd == 'alias':
                    continue  # Skip alias in loaded .xts command list
                # Truncate long descriptions
                short_desc = desc.split('\n')[0][:80]
                console.print(f"  [bold green]{cmd:25}[/bold green] [dim]{short_desc}[/dim]")
            console.print(f"\n[dim]Use [bold]xts {self._alias_name if hasattr(self, '_alias_name') else '<command>'} <command> --help[/bold] for more information[/dim]")
            sys.exit(1)
        else:
            # Default error handling
            self.print_usage(sys.stderr)
            from xts_core.utils import error as rich_error
            rich_error(f"{message}")


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
        self._plugins = []  # Removed XTSAllocatorClient - use aliased .xts files instead
        self._used_args = []


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

    def _parse_first_arg(self):
        """
        Parse CLI arguments and set up argparse for all commands.
        - Handles 'alias' subcommands immediately.
        - Resolves first argument as an .xts config file or alias.
        - Loads YAML/plugin commands after config is loaded.
        
        Returns:
            list: Remaining arguments after parsing, including the command name.
        """
        # If no arguments provided, show help with available aliases
        if len(sys.argv) == 1:
            console = Console()
            
            # Show available aliases FIRST (most important)
            aliases = xts_alias.list_aliases()
            if aliases:
                console.print("\n[bold yellow]Available aliases:[/bold yellow]")
                for alias_name in sorted(aliases.keys()):
                    console.print(f"  [bold cyan]{alias_name}[/bold cyan]")
                console.print("\n[dim]Use [bold]xts <alias>[/bold] to load commands from an alias[/dim]")
                console.print("[dim]Example: [bold cyan]xts allocator --help[/bold cyan][/dim]")
                console.print("\n[dim]To manage aliases: [bold]xts alias [add|list|remove][/bold][/dim]")
            else:
                # No aliases yet, show how to add them
                console.print("\n[yellow]No aliases configured yet.[/yellow]")
                console.print("\n[bold]Get started:[/bold]")
                console.print("  [cyan]xts alias add <name> <path>[/cyan]  - Add a single .xts file")
                console.print("  [cyan]xts alias add .[/cyan]              - Add all .xts files in current directory")
                console.print("  [cyan]xts alias add -r <dir>[/cyan]       - Recursively add .xts files")
                console.print("\n[dim]Example: [bold cyan]xts alias add allocator http://server:5000/xts_allocator.xts[/bold cyan][/dim]")
            
            sys.exit(0)
        
        # quick parser for alias commands
        pre_parser = RichArgumentParser(prog="xts", add_help=True)
        pre_subparsers = pre_parser.add_subparsers(dest="command", required=True)
        self._add_alias_subcommands(pre_subparsers)

        if len(sys.argv) > 1 and sys.argv[1] == "alias":
            parsed_args = pre_parser.parse_args(sys.argv[1:])  # parse everything after 'xts'
            self._handle_alias(parsed_args)
            sys.exit(0)

        # resolve first arg as config/alias
        resolved_alias_name = None
        if len(sys.argv) > 1:
            first_arg = sys.argv[1]
            resolved_alias_name = first_arg  # Store for display
            resolved = self._resolve_first_arg(first_arg)
            if not resolved:
                self._find_xts_config()
        else:
            self._find_xts_config() 

        # full parser with YAML/plugin commands
        parser = RichArgumentParser(prog="xts")
        subparsers = parser.add_subparsers(dest="command", required=True)
        self._add_alias_subcommands(subparsers)

        command_list = list(self._get_command_choices())
        for command, description in command_list:
            subparsers.add_parser(command,
                                  help=description,
                                  add_help=False)
        
        # Pass command list and alias name to parser for nice error messages
        parser.set_command_list(command_list)
        if resolved_alias_name:
            parser.set_alias_name(resolved_alias_name)
        
        # Parsing here will raise SystemExit() early if an invalid command is used or
        # if --help is called with no other arguments.
        parsed_args, remaining = parser.parse_known_args()
        return [parsed_args.command] + remaining

    def _resolve_first_arg(self, arg: str) -> str | None:
        """
        Resolve the first CLI argument into a usable .xts config path or alias.

        If:
        - "alias" → return the literal string "alias".
        - Local file ending with ".xts" → set self.xts_config to this path.
        - Named alias from ~/.xts/aliases.json → resolve to its target.
        - Remote URL (http/https) → fetch and cache the file locally, 
            then set self.xts_config to the cached path.

        Args:
            arg (str): The first CLI argument passed to the xts command.

        Returns:
            str (None): 
                - "alias" if the subcommand is 'alias'.
                - The resolved .xts file path (local or cached).
                - None if no resolution could be performed.
        """
        if arg == "alias":
            return "alias"

        if os.path.exists(arg) and arg.endswith(".xts"):
            self.xts_config = arg
            self._used_args.append(arg)
            sys.argv.pop(1)
            return arg

        try:
            if os.path.exists(xts_alias.ALIAS_FILE):
                with open(xts_alias.ALIAS_FILE) as f:
                    aliases = json.load(f)
            else:
                aliases = {}

            if arg in aliases:
                arg = aliases[arg]

            if is_url(arg):
                resolved = xts_alias.fetch_url_to_cache(arg)
            else:
                resolved = arg

            if resolved and resolved.endswith(".xts"):
                self.xts_config = resolved
                self._used_args.append(arg)
                sys.argv.pop(1)
                return resolved

        except Exception:
            pass

        return None
    
    def _handle_alias(self, parsed_args):
        """
        Execute alias subcommands (add, list, remove).
        - If the user provides an absolute path, use it as-is.
        - If the user provides a relative path, resolve it against the
            current working directory.
        - If the user provides a directory path (., *.xts, or directory),
            recursively find all .xts files and add them as aliases.
        """
        if parsed_args.alias_cmd == "add":
            name = parsed_args.name
            path = parsed_args.path
            recursive = getattr(parsed_args, 'recursive', False)

            # Check if this is directory-based batch addition
            if path is None or name in ['.', '*.xts'] or os.path.isdir(name):
                # Directory-based alias creation
                search_dir = name if name not in ['.', '*.xts'] else '.'
                info(f"Scanning {search_dir} for .xts files{'(recursive)' if recursive else ''}...")
                xts_files = xts_alias.find_xts_files(search_dir, recursive=recursive)
                
                if not xts_files:
                    warning(f"No .xts files found in {search_dir}")
                    return
                
                added_count = 0
                for xts_file in xts_files:
                    # Generate alias name from filename without extension
                    base_name = os.path.splitext(os.path.basename(xts_file))[0]
                    xts_alias.add_alias(base_name, xts_file)
                    success(f"  + [bold cyan]{base_name}[/bold cyan] -> [dim]{xts_file}[/dim]")
                    added_count += 1
                
                success(f"\n+ Added [bold]{added_count}[/bold] alias(es) from [cyan]{search_dir}[/cyan]")
                # Show usage hint
                console = Console()
                console.print(f"\n[dim]Use [bold cyan]xts <alias>[/bold cyan] to load commands[/dim]")
                if added_count == 1:
                    console.print(f"[dim]Example: [bold cyan]xts {base_name} --help[/bold cyan][/dim]")
                else:
                    console.print(f"[dim]Example: [bold cyan]xts --help[/bold cyan] to see all aliases[/dim]")
            else:
                # Single file/URL alias
                if not is_url(path):
                    path = os.path.abspath(path)
                xts_alias.add_alias(name, path)
                success(f"+ Alias [bold cyan]{name}[/bold cyan] -> [dim]{path}[/dim]")
                # Show usage hint
                console = Console()
                console.print(f"[dim]Use: [bold cyan]xts {name} --help[/bold cyan][/dim]")

        elif parsed_args.alias_cmd == "list":
            aliases = xts_alias.list_aliases()
            if not aliases:
                warning("No aliases defined. Use [bold]xts alias add[/bold] to create one.")
            else:
                info(f"\nRegistered aliases ({len(aliases)}):")
                for k, v in aliases.items():
                    success(f"  [bold cyan]{k}[/bold cyan] -> [dim]{v}[/dim]")
                print()

        elif parsed_args.alias_cmd == "remove":
            xts_alias.remove_alias(parsed_args.name)
            success(f"+ Removed alias [bold cyan]{parsed_args.name}[/bold cyan]")

    def _add_alias_subcommands(self, subparsers):
        """
        Adds the 'alias' subcommand and its subcommands (add, list, remove)
        to the provided subparsers object.

        Args:
            subparsers (argparse._SubParsersAction): The subparsers object to attach alias commands to.
        """
        alias_parser = subparsers.add_parser('alias', help='Manage XTS aliases', formatter_class=RichHelpFormatter)
        alias_subparsers = alias_parser.add_subparsers(dest='alias_cmd', required=True)

        # alias add <name> <path> or alias add <directory> [-r]
        add_parser = alias_subparsers.add_parser('add', 
            help='Add alias(es). Use: add <name> <path> for single, or add <dir> [-r] for batch',
            formatter_class=RichHelpFormatter)
        add_parser.add_argument('name', 
            help='Alias name, or directory path (., *.xts, ./path/) to add multiple')
        add_parser.add_argument('path', nargs='?', default=None,
            help='Path or URL (required for single alias, omit for directory mode)')
        add_parser.add_argument('-r', '--recursive', action='store_true',
            help='Recursively search for .xts files in subdirectories')

        # alias list
        list_parser = alias_subparsers.add_parser('list', help='List all aliases', formatter_class=RichHelpFormatter)

        # alias remove <name>
        remove_parser = alias_subparsers.add_parser('remove', help='Remove an alias', formatter_class=RichHelpFormatter)
        remove_parser.add_argument('name', help='Name of the alias to remove')
    
    def _find_xts_config(self):
        """
        Searches for an XTS configuration file in the current directory.
        If multiple files are found, calls _user_select_config to prompt the user.

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
                # No config and no plugins - let argparse show help
                pass
            else:
                warning('No config found. Continuing only with commands from plugins.')
        else:
            self.xts_config = xts_configs[0]

    def _user_select_config(self, choices):
        """
        Prompts the user to select one of multiple XTS configuration files.
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
            list[tuple]: List of tuples (command, description) for available commands.
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
        Extracts command sections from the loaded XTS configuration.

        Returns:
            dict: Dictionary containing only keys that represent command sections.
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