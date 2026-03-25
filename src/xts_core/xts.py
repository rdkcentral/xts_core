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
from typing import Optional

import yaml
try:
    from yaml import CSafeLoader as SafeLoader
except ImportError:
    from yaml import SafeLoader

import yaml.scanner
from yaml_runner import YamlRunner
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

__version__ = "2.0.0"

# Note: XTSAllocatorClient plugin removed in favor of centrally-managed
# .xts files from allocator servers. Use aliases instead:
#   xts alias add allocator http://server:5000/xts_allocator.xts

try:
    from . import utils as xts_utils
except:
    from xts_core import utils as xts_utils

try:
    from . import xts_alias
except:
    from xts_core import xts_alias


def info(message):
    return xts_utils.info(message)


def warning(message):
    return xts_utils.warning(message)


def success(message):
    return xts_utils.success(message)


def error(message):
    return xts_utils.error(message)


def is_url(value):
    return xts_utils.is_url(value)


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
            
            # Header with alias name
            if hasattr(self, '_alias_name'):
                header = Text()
                header.append(f"{self._alias_name}", style="bold cyan")
                header.append(" commands", style="dim")
                console.print(Panel(header, border_style="cyan", padding=(0, 1)))
                console.print()
            else:
                console.print("\n[bold yellow]Available commands:[/bold yellow]\n")
            
            # Display commands with colors and descriptions
            for cmd, desc in self._command_list:
                if cmd == 'alias':
                    continue  # Skip alias in loaded .xts command list
                
                # Get first line of description and truncate if too long
                if desc:
                    short_desc = desc.split('\n')[0]
                    if len(short_desc) > 70:
                        short_desc = short_desc[:67] + "..."
                else:
                    short_desc = ""
                
                # Color format: command in green, description in dim
                if short_desc:
                    console.print(f"  [bold green]{cmd:25}[/bold green] [dim]{short_desc}[/dim]")
                else:
                    console.print(f"  [bold green]{cmd}[/bold green]")
            
            # Footer with usage hint
            console.print()
            if hasattr(self, '_alias_name'):
                console.print(f"[dim]Use [bold cyan]xts {self._alias_name} <command> --help[/bold cyan] for more information[/dim]")
            else:
                console.print(f"[dim]Use [bold]xts <command> --help[/bold] for more information[/dim]")
            sys.exit(1)
        else:
            # Default error handling
            self.print_usage(sys.stderr)
            error(f"{message}")


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
        # Load built-in plugins
        try:
            from .plugins.xts_tools_plugin import XTSToolsPlugin
            self._plugins = [XTSToolsPlugin]
        except ImportError:
            self._plugins = []
        self._used_args = []
        self._runtime_context = {"alias_name": None}


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
                raise SystemExit(1)
            except yaml.scanner.ScannerError as e:
                error(f'The xts file is incorrectly formatted: {config}')
                raise SystemExit(1)
        else:
            error('xts config specified does not exist')
            raise SystemExit(1)

    def _print_main_help(self):
        """Print the main help message listing all valid commands."""
        console = Console()
        header = Text()
        header.append("XTS ", style="bold cyan")
        header.append(f"v{__version__}", style="dim")
        console.print(Panel(header, border_style="cyan", padding=(0, 1)))
        console.print("\n[bold]eXtensible Test System[/bold]")
        console.print("A command-line tool for executing test commands from YAML configuration files.\n")
        console.print("[dim]Execute commands defined in .xts files using aliases for quick access.[/dim]\n")
        console.print("[bold yellow]Commands:[/bold yellow]")
        console.print(f"  [bold green]{'alias':<20}[/bold green] [dim]Manage aliases (add, list, remove, refresh, clean)[/dim]")
        console.print(f"  [bold green]{'guide':<20}[/bold green] [dim]Interactive XTS tutorial and training[/dim]")
        console.print(f"  [bold green]{'manual':<20}[/bold green] [dim]Feature summary and documentation links[/dim]")
        console.print(f"  [bold green]{'validate':<20}[/bold green] [dim]Validate .xts file schema and syntax[/dim]")
        console.print(f"  [bold green]{'create':<20}[/bold green] [dim]Create new .xts file interactively[/dim]")
        aliases = xts_alias.list_aliases()
        if aliases:
            console.print("\n[bold yellow]Configured Aliases:[/bold yellow]")
            try:
                with open(xts_alias.get_alias_file_path()) as f:
                    alias_config = json.load(f)
            except:
                alias_config = {}
            for alias_name in sorted(aliases.keys()):
                alias_path = alias_config.get(alias_name, "")
                # Only handle alias_path if it's a string
                if isinstance(alias_path, str) and alias_path:
                    display_path = os.path.basename(alias_path) if not is_url(alias_path) else alias_path
                    console.print(f"  [bold cyan]{alias_name:<20}[/bold cyan] [dim]{display_path}[/dim]")
                elif not alias_path:
                    console.print(f"  [bold cyan]{alias_name}[/bold cyan]")
                else:
                    # If alias_path is not a string, skip or print a warning
                    console.print(f"  [bold cyan]{alias_name:<20}[/bold cyan] [dim][invalid alias entry][/dim]")
            console.print("\n[bold]Usage:[/bold]")
            console.print("  [cyan]xts <alias> <command> [options][/cyan]")
            console.print("  [cyan]xts <alias> --help[/cyan]              - Show commands for an alias")
            console.print("  [cyan]xts alias list[/cyan]                  - Show all aliases with details")
            console.print("\n[dim]Example: [bold cyan]xts allocator list_slots[/bold cyan][/dim]")
        else:
            console.print("\n[yellow]No aliases configured yet.[/yellow]")
            console.print("\n[bold]Get started:[/bold]")
            console.print("  [cyan]xts alias add <name> <path>[/cyan]  - Add a single .xts file")
            console.print("  [cyan]xts alias add .[/cyan]              - Add all .xts files in current directory")
            console.print("  [cyan]xts alias add -r <dir>[/cyan]       - Recursively add .xts files")
            console.print("\n[dim]Example: [bold cyan]xts alias add allocator http://server:5000/xts_allocator.xts[/bold cyan][/dim]")
        console.print("\n[dim]For more information: [bold]xts --help[/bold] or [bold]xts alias --help[/bold][/dim]")

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
            self._print_main_help()
            sys.exit(0)
        
        # Handle --version flag
        if len(sys.argv) > 1 and sys.argv[1] in ['--version', '-v']:
            console = Console()
            console.print(f"[bold cyan]xts[/bold cyan] version [bold]{__version__}[/bold]")
            sys.exit(0)

        # Handle --help flag
        if len(sys.argv) > 1 and sys.argv[1] in ['--help', '-h']:
            self._print_main_help()
            sys.exit(0)
        
        # quick parser for alias commands
        pre_parser = RichArgumentParser(prog="xts", add_help=True)
        pre_parser.add_argument('--version', '-v', action='version', version=f'xts {__version__}')
        pre_subparsers = pre_parser.add_subparsers(dest="command", required=True)
        self._add_alias_subcommands(pre_subparsers)
        # self._add_proxy_subcommands(pre_subparsers)  # Proxy disabled

        if len(sys.argv) > 1 and sys.argv[1] == "alias":
            parsed_args = pre_parser.parse_args(sys.argv[1:])  # parse everything after 'xts'
            self._handle_alias(parsed_args)
            sys.exit(0)
        
        # if len(sys.argv) > 1 and sys.argv[1] == "proxy":
        #     parsed_args = pre_parser.parse_args(sys.argv[1:])  # parse everything after 'xts'
        #     self._handle_proxy(parsed_args)
        #     sys.exit(0)

        # Early dispatch for plugin positionals (validate, create, edit, etc.)
        # Core commands are protected and cannot be overridden by plugins.
        _CORE_COMMANDS = {"alias", "--help", "-h", "--version", "-v"}  # Proxy removed
        if len(sys.argv) > 1 and sys.argv[1] not in _CORE_COMMANDS:
            for plugin_cls in self._plugins:
                if sys.argv[1] in plugin_cls().provided_positionals:
                    return sys.argv[1:]

        # resolve first arg as config/alias
        resolved_alias_name = None
        if len(sys.argv) > 1:
            first_arg = sys.argv[1]
            resolved_alias_name = first_arg  # Store for display
            resolved = self._resolve_first_arg(first_arg)
            if not resolved and self._xts_config is None:
                self._find_xts_config()
        elif self._xts_config is None:
            self._find_xts_config() 

        # full parser with YAML/plugin commands
        parser = RichArgumentParser(prog="xts")
        subparsers = parser.add_subparsers(dest="command", required=True)
        self._add_alias_subcommands(subparsers)
        # self._add_proxy_subcommands(subparsers)  # Proxy disabled

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
            return arg

        # Local file provided directly
        if os.path.exists(arg) and arg.endswith(".xts"):
            self.xts_config = arg
            self._used_args.append(arg)
            if len(sys.argv) > 1 and sys.argv[1] == arg:
                sys.argv.pop(1)
            return os.path.basename(arg)

        # Known alias
        aliases = xts_alias.list_aliases()
        if arg in aliases:
            resolved = aliases[arg]
            if resolved and resolved.endswith(".xts"):
                self.xts_config = resolved
                self._used_args.append(arg)
                self._runtime_context["alias_name"] = arg
                if len(sys.argv) > 1 and sys.argv[1] == arg:
                    sys.argv.pop(1)
                return arg

        # Remote URL
        if is_url(arg):
            xts_alias.ensure_dirs()
            cache_path = xts_alias.get_cache_path(arg, "remote")
            success, _ = xts_alias.fetch_remote_file(arg, cache_path)
            if success and os.path.exists(cache_path):
                self.xts_config = cache_path
                self._used_args.append(arg)
                if len(sys.argv) > 1 and sys.argv[1] == arg:
                    sys.argv.pop(1)
                return arg

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
            proxy_name = getattr(parsed_args, 'proxy', None)
            kwargs = {"recursive": recursive}
            if proxy_name is not None:
                kwargs["proxy_name"] = proxy_name

            # Keep behavior thin here; xts_alias.add_alias handles file/url/dir logic.
            if path is not None and not is_url(path):
                path = os.path.abspath(path)

            xts_alias.add_alias(name, path, **kwargs)
            success(f"+ Alias [bold cyan]{name}[/bold cyan] -> [dim]{path}[/dim]")

        elif parsed_args.alias_cmd == "list":
            check_updates = getattr(parsed_args, 'check_updates', False)
            aliases = xts_alias.list_aliases(check_updates=check_updates)
            if not aliases:
                warning("No aliases defined. Use [bold]xts alias add[/bold] to create one.")
            else:
                if not check_updates:
                    info(f"\nRegistered aliases ({len(aliases)}):")
                    for k, v in aliases.items():
                        success(f"  [bold cyan]{k}[/bold cyan] -> [dim]{v}[/dim]")
                    print()
                    info("[dim]Tip: Use [bold cyan]xts alias list --check[/bold cyan] to check for updates[/dim]")
                else:
                    metadata = xts_alias.load_metadata()
                    for alias_name in aliases:
                        xts_alias.check_for_updates(alias_name, metadata.get(alias_name, {}))
                    print()  # Newline after update check output

        elif parsed_args.alias_cmd == "remove":
            xts_alias.remove_alias(parsed_args.name)
            success(f"+ Removed alias [bold cyan]{parsed_args.name}[/bold cyan]")

        elif parsed_args.alias_cmd == "refresh":
            if parsed_args.name == "all":
                # Refresh all aliases
                aliases = xts_alias.list_aliases()
                refreshed = 0
                for name in aliases:
                    if xts_alias.refresh_alias(name):
                        refreshed += 1
                success(f"+ Refreshed {refreshed}/{len(aliases)} aliases")
            else:
                # Refresh single alias
                xts_alias.refresh_alias(parsed_args.name)

        elif parsed_args.alias_cmd == "clean":
            xts_alias.clean_broken_aliases()

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
        add_parser.add_argument('--proxy', type=str, default=None,
            help='Proxy name (reference to configured proxy, e.g., --proxy sky)')

        # alias list [--check]
        list_parser = alias_subparsers.add_parser('list', help='List all aliases', formatter_class=RichHelpFormatter)
        list_parser.add_argument('--check', '-c', action='store_true', dest='check_updates',
            help='Check for updates (slower)')

        # alias remove <name>
        remove_parser = alias_subparsers.add_parser('remove', help='Remove an alias', formatter_class=RichHelpFormatter)
        remove_parser.add_argument('name', help='Name of the alias to remove')

        # alias refresh <name|all>
        refresh_parser = alias_subparsers.add_parser('refresh', help='Refresh alias from source', formatter_class=RichHelpFormatter)
        refresh_parser.add_argument('name', help='Alias name to refresh, or "all" for all aliases')

        # alias clean
        clean_parser = alias_subparsers.add_parser('clean', help='Find and remove broken aliases', formatter_class=RichHelpFormatter)
    
    def _add_proxy_subcommands(self, subparsers):
        """
        Adds the 'proxy' subcommand and its subcommands (add, list, remove)
        to the provided subparsers object.

        Args:
            subparsers (argparse._SubParsersAction): The subparsers object to attach proxy commands to.
        """
        pass  # Proxy command disabled
    
    def _handle_proxy(self, parsed_args):
        """
        Execute proxy subcommands (add, list, remove).
        """
        if parsed_args.proxy_cmd == "add":
            name = parsed_args.name
            proxy = parsed_args.proxy
            proxy_type = getattr(parsed_args, 'type', 'http')
            username = getattr(parsed_args, 'username', None)
            password = getattr(parsed_args, 'password', None)
            
            xts_alias.add_proxy(name, proxy, proxy_type=proxy_type, username=username, password=password)

        elif parsed_args.proxy_cmd == "list":
            proxies = xts_alias.list_proxies()
            if not proxies:
                warning("No proxies configured. Use [bold]xts proxy add[/bold] to create one.")
            else:
                info(f"\nConfigured proxies ({len(proxies)}):")
                for name, config in proxies.items():
                    proxy_url = config.get('proxy', '')
                    proxy_type = config.get('type', 'http').upper()
                    username = config.get('username', '')
                    if username:
                        success(f"  [bold cyan]{name}[/bold cyan] ({proxy_type}) -> {proxy_url} (user: {username})")
                    else:
                        success(f"  [bold cyan]{name}[/bold cyan] ({proxy_type}) -> {proxy_url}")
                print()

        elif parsed_args.proxy_cmd == "remove":
            xts_alias.remove_proxy(parsed_args.name)
            success(f"+ Removed proxy [bold cyan]{parsed_args.name}[/bold cyan]")
    
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
            warning('No config found. Continuing only with commands from plugins.')
        else:
            self.xts_config = os.path.join(os.getcwd(), xts_configs[0])

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
        print('Select the .xts file to use:\n')
        for idx, filename in enumerate(choices, start=1):
            print(f'  {idx}. {filename}')

        selected = input('\nEnter choice number: ').strip()
        try:
            index = int(selected) - 1
        except ValueError:
            error('Invalid selection')
            raise SystemExit(1)

        if index < 0 or index >= len(choices):
            error('Invalid selection')
            raise SystemExit(1)

        self.xts_config = os.path.join(os.getcwd(), choices[index])
        raise SystemExit(0)

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
            # Support both styles:
            # 1) commands: {cmd1: {...}}
            # 2) top-level command groups: {features: {...}, ...}
            if "commands" in self._command_sections and isinstance(self._command_sections["commands"], dict):
                for command, details in self._command_sections["commands"].items():
                    if isinstance(details, dict):
                        choices_with_desc.append((command, details.get('description', '')))
            else:
                for command, details in self._command_sections.items():
                    if isinstance(details, dict):
                        description = details.get('description', '')
                        choices_with_desc.append((command, description))

        # additional commands provided by plugins
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

    def _command_tree(self) -> dict:
        """Return the command tree used by the runtime."""
        if "commands" in self._command_sections and len(self._command_sections) == 1:
            commands = self._command_sections.get("commands", {})
            return commands if isinstance(commands, dict) else {}
        return self._command_sections

    def _find_node_for_path(self, path_parts: list[str]) -> Optional[dict]:
        """Find a nested command/group node for a command path."""
        if not path_parts:
            return None

        node: object = self._command_tree()
        for part in path_parts:
            if not isinstance(node, dict):
                return None
            if part not in node:
                return None
            node = node[part]

        return node if isinstance(node, dict) else None

    def _get_group_subcommands(self, node: dict) -> list[tuple[str, str]]:
        """Return direct child command/group entries for a node."""
        if not isinstance(node, dict):
            return []

        reserved = {
            "description", "brief", "command", "args", "arguments", "options",
            "params", "formatter", "environment", "working_directory", "timeout",
            "schema_version", "version", "changelog"
        }
        subcommands = []
        for key, value in node.items():
            if key in reserved:
                continue
            if isinstance(value, dict):
                subcommands.append((key, value.get("description", "")))
        return subcommands

    def _show_group_usage_if_needed(self, args: list[str]) -> bool:
        """Show group usage if args point to a group node without a command."""
        if not args:
            return False
        if args[0].startswith("-"):
            return False

        node = self._find_node_for_path(args)
        if node is None:
            return False

        if "command" in node:
            return False

        subcommands = self._get_group_subcommands(node)
        if not subcommands:
            return False

        alias_name = self._runtime_context.get("alias_name") or "xts"
        prefix = f"xts {alias_name}" if alias_name != "xts" else "xts"
        command_path = " ".join(args)

        console = Console()
        console.print(f"\n[bold yellow]Subcommands for '{command_path}':[/bold yellow]")
        for name, desc in subcommands:
            if desc:
                console.print(f"  [bold green]{name:<20}[/bold green] [dim]{desc}[/dim]")
            else:
                console.print(f"  [bold green]{name}[/bold green]")
        console.print(f"\n[dim]Use [bold cyan]{prefix} {command_path} <subcommand>[/bold cyan][/dim]")
        return True

    @staticmethod
    def _inject_standard_functions(config: dict) -> dict:
        """Merge standard library functions into the config.

        Standard functions are added first, then user-defined functions
        override them, ensuring user definitions always take priority.
        """
        from .standard_functions import get_standard_functions

        merged = config.copy()
        std = get_standard_functions()
        std.update(config.get('functions', {}))
        merged['functions'] = std
        return merged

    def run(self):
        """Run the XTS app.

        Raises:
            SystemExit: Raised when unrecogised arguments are given.
        """
        args = self._parse_first_arg()
        # Validate filename for create command
        if args and args[0] == "create":
            # Only allow valid filenames, not options like '--help'
            if len(args) > 1:
                filename = args[1]
                import re
                # Disallow filenames that start with '-' or are not .xts files
                if filename.startswith("-") or not re.match(r'^[\w\-.]+\.xts$', filename):
                    error(f"Invalid filename for create: {filename}")
                    sys.exit(1)
        if plugins := list(filter(lambda x: args[0] in x().provided_positionals,self._plugins)):
            for plugin in plugins:
                plugin().run(args)
        else:
            try:
                if self._show_group_usage_if_needed(args):
                    raise SystemExit(0)

                config = self._inject_standard_functions(self._command_tree())
                yaml_runner = YamlRunner(config,
                        program='xts',
                        hierarchical=True,
                        fail_fast=True)
                _,_,exit_code = yaml_runner.run(args)
                sys.exit(sorted(exit_code)[-1])
            except Exception as e:
                # This code should be unreachable, but is handled just in case.
                error('An unrecognised command has caused and error\n\n'+
                      f'Command Args: [{" ".join(args)}]\n\n'+
                      str(e))

def main():
    XTS().run()

if __name__ == "__main__":
    main()
