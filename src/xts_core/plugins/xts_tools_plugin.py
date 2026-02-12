#!/usr/bin/env python3
#** *****************************************************************************
# *
# * If not stated otherwise in this file or this component's LICENSE file the
# * following copyright and licenses apply:
# *
# * Copyright 2026 RDK Management
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

"""XTS Tools Plugin - Commands for working with .xts files.

Provides:
- validate: Validate .xts file schema and syntax
- create: Interactive wizard to create new .xts files
- edit: Interactive editor for existing .xts files
- functions: List and inspect standard library functions
"""

import sys
from pathlib import Path

try:
    from ..utils import info, error, success
    from ..xts_validator import validate_command
    from ..xts_wizard import XTSWizard
    from .base_plugin import BaseXTSPlugin as Plugin
except:
    from xts_core.utils import info, error, success
    from xts_core.xts_validator import validate_command
    from xts_core.xts_wizard import XTSWizard
    from xts_core.plugins.base_plugin import BaseXTSPlugin as Plugin


class XTSToolsPlugin(Plugin):
    """Plugin providing tools for managing .xts files."""
    
    def __init__(self):
        """Initialize the tools plugin."""
        super().__init__()
        self.provided_positionals = ['validate', 'create', 'edit', 'functions']
        self.provided_args = []  # No args, only positionals
    
    def run(self, args: list):
        """Execute the appropriate tools command.
        
        Args:
            args: Command-line arguments starting with the command name
        """
        if not args:
            self._print_help()
            sys.exit(1)
        
        command = args[0]
        
        if command == 'validate':
            self._validate(args[1:])
        elif command == 'create':
            self._create(args[1:])
        elif command == 'edit':
            self._edit(args[1:])
        elif command == 'functions':
            self._functions_cmd(args[1:])
        else:
            error(f"Unknown tools command: {command}")
            self._print_help()
            sys.exit(1)
    
    def _print_help(self):
        """Print help for tools commands."""
        print("\nXTS Tools - Manage .xts configuration files\n")
        print("Commands:")
        print("  validate <file>      Validate .xts file schema and syntax")
        print("                       Options: -v/--verbose, --json")
        print()
        print("  create <file>        Create new .xts file interactively")
        print("                       Options: --resume (resume from saved state)")
        print()
        print("  edit <file>          Edit existing .xts file interactively")
        print()
        print("  functions [list|show] View standard library functions")
        print("                       list: Show all standard functions")
        print("                       show <name>: Show function details")
        print()
        print("Examples:")
        print("  xts validate myconfig.xts")
        print("  xts validate myconfig.xts -v")
        print("  xts create newproject.xts")
        print("  xts edit myconfig.xts")
        print("  xts create newproject --resume  # Resume after CTRL-C")
        print("  xts functions list")
        print("  xts functions show format_json")
        print()
    
    def _validate(self, args: list):
        """Validate an .xts file."""
        if not args:
            error("File path required")
            print("\nUsage: xts validate <file> [-v|--verbose] [--json]")
            sys.exit(1)
        
        filepath = args[0]
        verbose = '-v' in args or '--verbose' in args
        json_output = '--json' in args
        
        exit_code = validate_command(filepath, verbose, json_output)
        sys.exit(exit_code)
    
    def _create(self, args: list):
        """Create a new .xts file interactively."""
        if not args:
            error("File path required")
            print("\nUsage: xts create <file> [--resume]")
            sys.exit(1)
        
        filepath = args[0]
        resume = '--resume' in args
        
        # Ensure .xts extension
        if not filepath.endswith('.xts'):
            filepath += '.xts'
        
        # Check if file already exists
        if Path(filepath).exists() and not resume:
            response = input(f"File '{filepath}' exists. Overwrite? (y/n): ").strip().lower()
            if response != 'y':
                info("Cancelled")
                sys.exit(0)
        
        wizard = XTSWizard(filepath, edit_mode=False)
        exit_code = wizard.run(resume=resume)
        sys.exit(exit_code)
    
    def _edit(self, args: list):
        """Edit an existing .xts file interactively."""
        if not args:
            error("File path required")
            print("\nUsage: xts edit <file>")
            sys.exit(1)
        
        filepath = args[0]
        
        if not Path(filepath).exists():
            error(f"File not found: {filepath}")
            sys.exit(1)
        
        wizard = XTSWizard(filepath, edit_mode=True)
        exit_code = wizard.run(resume=False)
        sys.exit(exit_code)

    def _functions_cmd(self, args: list):
        """List and inspect standard library functions."""
        try:
            from ..standard_functions import get_standard_functions
        except ImportError:
            from xts_core.standard_functions import get_standard_functions

        sub = args[0] if args else 'list'

        if sub in ('list', '-h', '--help'):
            self._functions_list(get_standard_functions())
        elif sub == 'show':
            if len(args) < 2:
                error("Function name required")
                print("\nUsage: xts functions show <name>")
                sys.exit(1)
            self._functions_show(args[1], get_standard_functions())
        else:
            # Treat unknown subcommand as a function name to show
            self._functions_show(sub, get_standard_functions())

    @staticmethod
    def _functions_list(functions: dict):
        """List all standard functions."""
        from rich.console import Console
        from rich.panel import Panel

        console = Console()
        console.print(Panel(
            f"[bold cyan]Standard Functions[/bold cyan]  [dim]({len(functions)} available)[/dim]",
            border_style="cyan",
            padding=(0, 1),
        ))
        console.print()
        for name in sorted(functions):
            desc = functions[name].get('description', '')
            console.print(f"  [bold green]{name:25}[/bold green] {desc}")
            console.print()
        console.print("[dim]Use [bold cyan]xts functions show <name>[/bold cyan] for details[/dim]")
        console.print("[dim]Available in all .xts files via [bold]{{function_name}}[/bold] syntax[/dim]")

    @staticmethod
    def _functions_show(name: str, functions: dict):
        """Show details of a specific standard function."""
        from rich.console import Console

        console = Console()
        if name not in functions:
            error(f"Unknown standard function: '{name}'")
            info("Use 'xts functions list' to see available functions")
            sys.exit(1)

        func = functions[name]
        console.print(f"\n[bold cyan]{name}[/bold cyan]")
        console.print(f"  [dim]Description:[/dim] {func.get('description', 'No description')}")
        console.print(f"  [dim]Command:[/dim]     [green]{func['command']}[/green]")
        console.print(f"\n  [dim]Usage in .xts file:[/dim]")
        console.print(f"    [cyan]command: some_cmd | {{{{{name}}}}}[/cyan]")
        console.print()
