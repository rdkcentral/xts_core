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
import threading
import time

import rich

def info(info_message: str):
    """
    Prints a Yellow informational message.

    Args:
        info_message (str): The informational message to be printed.
    """
    rich.print(f'[yellow]{info_message}[/yellow]')

def error(error_message: str):
    """
    Prints a Red error message and exits with exit code 1.

    Args:
        error_message (str): The error message to be printed.

    Raises:
        SystemExit: Exits the program due to the error. Exit code 1.
    """
    rich.print(f'[red][bold]ERROR:[/bold] {error_message}[/red]')
    raise SystemExit(1)

def warning(warning_message:str):
    """
    Print an orange warning message.

    Args:
        warning_message (str): Message to be printed as a warning.
    """
    rich.print(f'[dark_orange][bold]{warning_message}[/bold][/dark_orange]')

def is_url(s):
    """Check if a string is a URL.

    Args:
        s: The string to check.

    Returns:
        True if `s` starts with http:// or https://, otherwise False.
    """
    return s.startswith("http://") or s.startswith("https://")
