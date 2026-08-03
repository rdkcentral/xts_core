"""Reusable interactive demo helpers for the XTS CLI."""

import sys

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
    run_command = f'xts {alias_name} run hello_world'
    remove_command = f'xts alias remove {alias_name}'

    print()
    info('Section 1: Add a demo alias from the public example URL.')
    info(f'  Command: {add_command}')
    input('Press Enter to execute this command and continue... ')
    try:
        run_demo_alias_builtin(['add', '--name', alias_name, example_url])
    except Exception as exc:
        error(f'Failed to add demo alias: {exc}')

    print()
    info('Section 2: List available aliases.')
    info(f'  Command: {list_command}')
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

    print()
    info('Section 3: Run the demo alias command.')
    info(f'  Command: {run_command}')
    input('Press Enter to execute this command and continue... ')
    try:
        _, _, exit_code = yaml_runner.run(['run', 'hello_world'])
        if exit_code and any(int(code) != 0 for code in exit_code):
            info(f'Command failed: {run_command}')
    except SystemExit:
        pass
    except Exception as exc:
        error(f'Failed to run demo alias command: {exc}')

    print()
    info('Section 4: Remove the demo alias.')
    info(f'  Command: {remove_command}')
    input('Press Enter to execute this command and continue... ')
    try:
        run_demo_alias_builtin(['remove', alias_name])
    except Exception as exc:
        error(f'Failed to remove demo alias: {exc}')

    print()
    info('Demo finished. You can now add your own aliases with xts alias add --name <alias> <path-or-url>.')
