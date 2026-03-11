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
- guide: Interactive training system for learning XTS
- manual: Feature summary with links to documentation
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
        self.provided_positionals = ['validate', 'create', 'edit', 'guide', 'manual', 'remote']
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
        # 'functions' command disabled
        elif command == 'guide':
            if args[1:] and args[1] == 'learn':
                self._learn_cmd(args[2:])
            else:
                self._guide(args[1:])
        elif command == 'manual':
            self._manual(args[1:])
        elif command == 'remote':
            self._remote_tools_cmd(args[1:])
        else:
            error(f"Unknown tools command: {command}")
            self._print_help()
            sys.exit(1)

    def _learn_cmd(self, args: list):
        """Learn command invoked from guide."""
        info("Learn command executed from guide.")
        print("Learn functionality is available.")
        sys.exit(0)

    def _remote_tools_cmd(self, args: list):
        """Remote tools command placeholder."""
        info("Remote tools command executed.")
        print("Remote tools functionality is available.")
        sys.exit(0)
    
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
        print("  guide [topic]        Interactive XTS training system")
        print("                       Topics: basics, commands, func, structure,")
        print("                       aliases, tools, advanced, quickref")
        print()
        print("  manual               Feature summary with links to documentation")
        print()
        print("Examples:")
        print("  xts validate myconfig.xts")
        print("  xts validate myconfig.xts -v")
        print("  xts create newproject.xts")
        print("  xts edit myconfig.xts")
        print("  xts create newproject --resume  # Resume after CTRL-C")
        print("  xts functions list")
        print("  xts functions show format_json")
        print("  xts guide                       # Start interactive tutorial")
        print("  xts guide basics first          # Your first .xts file")
        print("  xts manual                      # Feature summary and docs")
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

    def _guide(self, args: list):
        """Run the interactive XTS guide system.

        Loads the bundled guide.xts file and runs it through YamlRunner.
        Defaults to 'welcome' when no arguments are provided.
        """
        import yaml
        try:
            from yaml import CSafeLoader as SafeLoader
        except ImportError:
            from yaml import SafeLoader
        from yaml_runner import YamlRunner

        # Locate bundled guide.xts
        guide_path = Path(__file__).resolve().parent.parent / "data" / "guide.xts"

        if not guide_path.exists():
            error(f"Guide data not found: {guide_path}")
            sys.exit(1)

        # Load and parse
        with open(guide_path, 'r', encoding='utf-8') as f:
            config = yaml.load(f, SafeLoader)

        # Filter metadata keys to get command sections
        _METADATA_KEYS = {'brief', 'schema_version', 'version', 'changelog', 'command_groups'}
        command_sections = {}
        for key, value in config.items():
            if key not in _METADATA_KEYS and isinstance(value, dict):
                command_sections[key] = value

        # Inject standard functions
        try:
            from ..standard_functions import get_standard_functions
        except ImportError:
            from xts_core.standard_functions import get_standard_functions

        std = get_standard_functions()
        std.update(config.get('functions', {}))
        command_sections['functions'] = std

        # Default to 'welcome' when no args provided
        if not args:
            args = ['welcome']

        # Run through YamlRunner
        try:
            yaml_runner = YamlRunner(
                command_sections,
                program='xts guide',
                hierarchical=True,
                fail_fast=True
            )
            _, _, exit_codes = yaml_runner.run(args)
            sys.exit(sorted(exit_codes)[-1])
        except SystemExit:
            raise
        except Exception as e:
            error(f'Guide system error: {e}')
            sys.exit(1)

    def _manual(self, args: list):
        """Display XTS feature summary with links to documentation."""
        from rich.console import Console
        from rich.panel import Panel
        from rich.text import Text

        console = Console()

        header = Text()
        header.append("XTS Manual", style="bold cyan")
        header.append("  Feature Summary & Documentation", style="dim")
        console.print(Panel(header, border_style="cyan", padding=(0, 1)))

        console.print()
        console.print("[bold]XTS[/bold] is a flexible command orchestration system that transforms")
        console.print("YAML files into powerful, self-documenting CLI tools.\n")

        # Features
        console.print("[bold yellow]Core Features:[/bold yellow]")
        features = [
            ("YAML Configuration", "Define commands in portable, version-controlled .xts files"),
            ("Alias System", "Register .xts files as named aliases for quick access"),
            ("Remote Sources", "Install .xts files from HTTP URLs and GitHub repositories"),
            ("Hierarchical Commands", "Organize commands in nested groups (xts alias db backup)"),
            ("Passthrough Arguments", "Pass CLI args to commands via $@ substitution"),
            ("Standard Functions", "13 built-in formatters (format_json, highlight_errors, ...)"),
            ("Interactive Wizard", "Create .xts files with guided prompts (xts create)"),
            ("Schema Validation", "Validate .xts files for correctness (xts validate)"),
            ("Tab Completion", "Bash completion for commands, aliases, and subcommands"),
            ("Proxy Support", "Corporate proxy configuration for remote aliases"),
        ]
        for name, desc in features:
            console.print(f"  [bold green]{name:<25}[/bold green] [dim]{desc}[/dim]")

        console.print()
        console.print("[bold yellow]Built-in Commands:[/bold yellow]")
        commands = [
            ("xts guide", "Interactive tutorial with progressive lessons"),
            ("xts validate <file>", "Validate .xts file schema and syntax"),
            ("xts create <file>", "Interactive wizard to create .xts files"),
            ("xts edit <file>", "Interactive editor for existing .xts files"),
            ("xts functions list", "List standard library functions"),
            ("xts alias add|list|remove", "Manage aliases"),
        ]
        for cmd, desc in commands:
            console.print(f"  [bold cyan]{cmd:<28}[/bold cyan] [dim]{desc}[/dim]")

        # Documentation links
        console.print()
        console.print("[bold yellow]Documentation:[/bold yellow]")
        docs = [
            ("README.md", "Overview, installation, getting started"),
            ("CHANGELOG.md", "Version history and release notes"),
            ("COMMAND_HISTORY.md", "Command recall and history features"),
            ("CONTRIBUTING.md", "Contribution guidelines"),
            ("docs/TAB_COMPLETION.md", "Bash tab completion setup and usage"),
            ("docs/install_command.md", "Installation command specification"),
            ("docs/PROXY_FEATURE.md", "Proxy support for remote aliases"),
            ("docs/REPO_ANALYZER.md", "Repository analyzer tool"),
            ("docs/HTTP_ANALYSIS.md", "HTTP remote repository analysis"),
            ("docs/test_documentation.md", "Test specification and coverage"),
            ("examples/proxy_example.md", "Proxy configuration examples"),
        ]
        for path, desc in docs:
            console.print(f"  [bold]{path:<30}[/bold] [dim]{desc}[/dim]")

        console.print()
        console.print("[dim]Run [bold cyan]xts guide[/bold cyan] for an interactive tutorial[/dim]")
        console.print("[dim]Documentation files are in the XTS repository root[/dim]")
        console.print()
