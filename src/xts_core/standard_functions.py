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

"""Standard function library for XTS.

Provides commonly-used pipeline functions that are available in all .xts files
without needing to define them. User-defined functions with the same name
take priority over standard functions.

Usage in .xts files:
    commands:
      my_cmd:
        command: curl -s api/data | {{format_json}}

View available functions:
    xts functions list
    xts functions show format_json
"""

STANDARD_FUNCTIONS = {
    "format_json": {
        "description": "Pretty-print JSON with color (requires jq)",
        "command": "jq -C .",
    },
    "format_json_raw": {
        "description": "Pretty-print JSON without color (requires jq)",
        "command": "jq .",
    },
    "format_yaml": {
        "description": "Pretty-print YAML output (requires python3 + PyYAML)",
        "command": (
            "python3 -c \""
            "import sys, yaml; "
            "print(yaml.dump(yaml.safe_load(sys.stdin.read()), default_flow_style=False))"
            "\""
        ),
    },
    "format_table": {
        "description": "Format comma-separated output as aligned table",
        "command": "column -t -s ','",
    },
    "count_lines": {
        "description": "Count the number of lines in input",
        "command": "wc -l",
    },
    "sort_unique": {
        "description": "Sort input, count unique occurrences, sort by frequency",
        "command": "sort | uniq -c | sort -rn",
    },
    "trim": {
        "description": "Trim leading and trailing whitespace from each line",
        "command": "sed 's/^[[:space:]]*//;s/[[:space:]]*$//'",
    },
    "to_upper": {
        "description": "Convert input to uppercase",
        "command": "tr '[:lower:]' '[:upper:]'",
    },
    "to_lower": {
        "description": "Convert input to lowercase",
        "command": "tr '[:upper:]' '[:lower:]'",
    },
    "highlight_errors": {
        "description": "Highlight ERROR/FAIL patterns in red",
        "command": "grep --color=always -E 'ERROR|error|FAIL|fail|$'",
    },
    "extract_ips": {
        "description": "Extract IPv4 addresses from input",
        "command": "grep -oE '[0-9]+\\.[0-9]+\\.[0-9]+\\.[0-9]+'",
    },
    "strip_ansi": {
        "description": "Remove ANSI color/escape codes from input",
        "command": "sed 's/\\x1b\\[[0-9;]*m//g'",
    },
    "csv_to_json": {
        "description": "Convert CSV input to JSON array (requires python3)",
        "command": (
            "python3 -c \""
            "import csv, json, sys; "
            "reader = csv.DictReader(sys.stdin); "
            "print(json.dumps(list(reader), indent=2))"
            "\""
        ),
    },
}


def get_standard_functions():
    """Return a copy of the standard functions dictionary.

    Returns:
        dict: Standard function definitions keyed by name.
              Each value is a dict with 'command' and 'description'.
    """
    return STANDARD_FUNCTIONS.copy()


def get_standard_function_names():
    """Return the set of standard function names.

    Returns:
        set: Set of standard function name strings.
    """
    return set(STANDARD_FUNCTIONS.keys())
