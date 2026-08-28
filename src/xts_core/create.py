"""Interactive creation of XTS configuration files."""

from pathlib import Path

import yaml
from rich.prompt import Confirm, Prompt


def _prompt(message: str, default: str | None = None) -> str:
    """Read a non-empty value, using the default when the user presses Enter."""
    return Prompt.ask(message, default=default)


def _prompt_yes_no(message: str) -> bool:
    """Read a yes/no answer, defaulting to no."""
    return Confirm.ask(message, default=False)


def _prompt_command(command_number: int) -> tuple[str, dict[str, str]]:
    """Collect one command and return its name and XTS definition."""
    print(f"\nCommand {command_number}")
    name = _prompt("Command name")
    description = _prompt("Description", f"Run {name}.")
    command = _prompt("Shell command")
    return name, {"description": description, "command": command}


def run_create(output_path: str | None = None) -> int:
    """Run the interactive XTS file creation wizard."""
    print("Create an XTS configuration")
    path = Path(output_path or _prompt("Output file")).expanduser()

    if path.suffix.lower() != ".xts":
        print(f"Output file must use the .xts extension: {path}")
        return 1

    if path.exists() and not _prompt_yes_no(f"File already exists: {path}. Overwrite it?"):
        print(f"Cancelled; existing file was not changed: {path}")
        return 1

    section = _prompt("Command section")
    commands: dict[str, dict[str, str]] = {}
    command_number = 1
    while True:
        name, definition = _prompt_command(command_number)
        if name in commands:
            print(f"Command already exists: {name}")
            continue
        commands[name] = definition
        command_number += 1
        if not _prompt_yes_no("Add another command?"):
            break

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump({section: commands}, sort_keys=False, default_flow_style=False),
        encoding="utf-8",
    )
    print(f"Created XTS file: {path}")
    return 0