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

"""Interactive creation of XTS configuration files."""

from pathlib import Path

import yaml
from rich.prompt import Confirm, Prompt


def _prompt(
    message: str, default: str | None = None, required: bool = False
) -> str:
    """Read a value, optionally requiring the user to provide one."""
    while True:
        value = Prompt.ask(message, default=default)
        if not required or (value is not None and value.strip()):
            return value
        print(f"{message} cannot be blank.")


def _prompt_yes_no(message: str) -> bool:
    """Read a yes/no answer, defaulting to no."""
    return Confirm.ask(message, default=False)


def _prompt_command(command_number: int) -> tuple[str, dict[str, str]]:
    """Collect one command and return its name and XTS definition."""
    print(f"\nCommand {command_number}")
    name = _prompt("Command name")
    description = _prompt("Description", required=True)
    command = _prompt("Shell command")
    return name, {"description": description, "command": command}


def run_create(output_path: str | None = None) -> int:
    """Run the interactive XTS file creation wizard."""
    print("Create an XTS configuration")
    path = Path(output_path or _prompt("Output file")).expanduser()
    if not path.suffix:
        path = path.with_name(f"{path.name}.xts")

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

    if _prompt_yes_no("Add this file as an alias?"):
        from .xts_alias import add_alias_from_input

        alias_name = _prompt("Alias name", path.stem)
        add_alias_from_input(str(path), alias_name)
        print(f"Added alias: {alias_name}")

    return 0