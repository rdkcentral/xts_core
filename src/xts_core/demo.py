"""Reusable interactive demo helpers for the XTS CLI."""

import sys

import rich
from yaml_runner import YamlRunner

try:
    from . import xts_alias
except ImportError:
    from xts_core import xts_alias

try:
    from .xts_arg_parser import XTSArgumentParser
except ImportError:
    from xts_core.xts_arg_parser import XTSArgumentParser

try:
    from .utils import info, error
except ImportError:
    from xts_core.utils import info, error


def _format_demo_command(command: str) -> str:
    """Return a richly formatted command string for demo output."""
    return f'[bold bright_cyan]{command}[/bold bright_cyan]'


def _print_section_title(title: str) -> None:
    """Print a demo section title with a visible separator and bold black text."""
    rich.print()
    rich.print('[bold bright_white]______________________________________________________________[/bold bright_white]')
    rich.print()
    rich.print(f'[bold bright_white]{title}[/bold bright_white]')
    rich.print()


def _print_demo_command(command: str) -> None:
    """Print a highlighted demo command before execution."""
    rich.print()
    rich.print(f'[bold green]COMMAND TO EXECUTE:[/bold green] {_format_demo_command(command)}')


def _print_command_options(description: str, options: list[str] | None = None) -> None:
    """Print command option descriptions for demo commands."""
    rich.print(f'[dim]{description}[/dim]')
    if options:
        for option in options:
            rich.print(f'[dim]  • {option}[/dim]')


def _run_xts_help_command(argv: list[str]) -> int:
    """Run XTS with arguments and return the SystemExit code."""
    original_argv = sys.argv[:]
    try:
        sys.argv = ['xts', *argv]
        from xts_core.xts import XTS

        XTS().run()
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else 0
    finally:
        sys.argv = original_argv
    return 0


def run_demo_alias_builtin(argv: list[str]) -> int:
    """Execute the alias built-in flow with a parser object matching the CLI contract."""
    alias_parser = XTSArgumentParser(prog='xts alias')
    xts_alias.setup_alias_parser(alias_parser)
    original_argv = sys.argv[:]
    try:
        sys.argv = ['xts', 'alias', *argv]
        return xts_alias.run_alias_builtin(alias_parser)
    finally:
        sys.argv = original_argv


def run_demo(xts_instance) -> None:
    """Run the interactive XTS demo built-in command."""
    example_url = (
        'https://raw.githubusercontent.com/rdkcentral/xts_core/refs/heads/master/'
        'examples/hello_world.xts'
    )
    alias_name = 'example'

    info('Welcome to the XTS interactive demo!')
    info('This demo will add an alias from the public example URL, show the alias list, and run the example command.')
    print()

    add_command = f'xts alias add --name {alias_name} {example_url}'
    list_command = 'xts alias list'
    alias_help_command = f'xts {alias_name} --help'
    run_command = f'xts {alias_name} run hello_world'
    remove_command = f'xts alias remove {alias_name}'

    _print_section_title('Section 1: Show top-level help for XTS.')
    _print_demo_command('xts --help')
    _print_command_options(
        'Display the root XTS command help, including built-in commands and general options.',
        ['--help: Show this help message and exit.']
    )
    print()
    input('Press Enter to execute this command and continue... ')
    _run_xts_help_command(['--help'])

    _print_section_title('Section 2: Add a demo alias from the public example URL.')
    _print_demo_command(add_command)
    _print_command_options(
        'Add a named alias for an XTS configuration from a URL.',
        [
            'URI: remote .xts file to add as the alias source.',
            '--name <alias>: explicit alias name to store instead of the default derived name.',
        ]
    )
    print()
    input('Press Enter to execute this command and continue... ')
    try:
        run_demo_alias_builtin(['add', '--name', alias_name, example_url])
    except Exception as exc:
        error(f'Failed to add demo alias: {exc}')

    _print_section_title('Section 3: Show help for the demo alias.')
    _print_demo_command(alias_help_command)
    _print_command_options(
        'Display help for the named alias command, showing available subcommands or options for this alias.',
        ['--help: Show help for the alias command and exit.']
    )
    print()
    input('Press Enter to execute this command and continue... ')
    _run_xts_help_command([alias_name, '--help'])

    _print_section_title('Section 4: List available aliases.')
    _print_demo_command(list_command)
    _print_command_options(
        'List all aliases currently configured in ~/.xts/aliases.json.',
        ['list: display alias names and their source paths.']
    )
    print()
    input('Press Enter to execute this command and continue... ')
    run_demo_alias_builtin(['list'])

    resolved_xts_path = xts_alias.resolve_alias_to_xts_path(alias_name)
    if resolved_xts_path is None:
        error(f'Failed to resolve alias for demo execution: {alias_name}')
        return

    xts_instance.xts_config = resolved_xts_path
    try:
        yaml_runner = YamlRunner(
            xts_instance._command_sections,
            program='xts',
            hierarchical=True,
            fail_fast=True,
            parser_class=XTSArgumentParser
        )
    except TypeError:
        yaml_runner = YamlRunner(
            xts_instance._command_sections,
            program='xts',
            hierarchical=True,
            fail_fast=True
        )

    _print_section_title('Section 5: Run the demo alias command.')
    _print_demo_command(run_command)
    _print_command_options(
        'Run the `hello_world` command from the alias-defined XTS file.',
        ['run hello_world: execute the hello_world command section in the alias.']
    )
    print()
    input('Press Enter to execute this command and continue... ')
    try:
        _, _, exit_code = yaml_runner.run(['run', 'hello_world'])
        if exit_code and any(int(code) != 0 for code in exit_code):
            info(f'Command failed: {run_command}')
    except SystemExit:
        pass
    except Exception as exc:
        error(f'Failed to run demo alias command: {exc}')

    _print_section_title('Section 6: Alias removal is optional.')
    _print_demo_command(remove_command)
    _print_command_options(
        'This command removes the alias from your local alias list, but it will not be executed by the demo.',
        ['<alias>: name of the alias to remove.']
    )
    info('The alias is still available after this demo. Run the above command if you want to remove it later.')

    print()
    info('Demo finished. You can now add your own aliases with xts alias add --name <alias> <path-or-url>.')
