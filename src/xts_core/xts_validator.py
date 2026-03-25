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

"""XTS configuration file validator.

Validates .xts files against the JSON schema and performs additional checks
for command syntax, placeholder consistency, and best practices.
"""

import json
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Any

import yaml
try:
    from yaml import CSafeLoader as SafeLoader
except ImportError:
    from yaml import SafeLoader

try:
    import jsonschema
    JSONSCHEMA_AVAILABLE = True
except ImportError:
    JSONSCHEMA_AVAILABLE = False

try:
    from .utils import error, warning, success, info
except:
    from xts_core.utils import error, warning, success, info


class XTSValidator:
    """Validates XTS configuration files."""
    
    def __init__(self):
        """Initialize validator with schema."""
        schema_path = Path(__file__).parent / "xts_schema.json"
        if schema_path.exists():
            with open(schema_path) as f:
                self.schema = json.load(f)
        else:
            self.schema = None
            warning("Schema file not found - basic validation only")

        self._top_level_reserved = {
            "brief", "schema_version", "version", "changelog", "functions", "commands", "description"
        }
        self._node_reserved = {
            "description", "brief", "command", "args", "arguments", "options", "params",
            "formatter", "environment", "working_directory", "timeout"
        }

    def _extract_commands(self, config: Dict) -> Dict:
        """Return command definitions from either modern or hierarchical config styles."""
        commands = config.get("commands")
        if isinstance(commands, dict) and commands:
            return commands

        extracted = {}
        for key, value in config.items():
            if key in self._top_level_reserved:
                continue
            if isinstance(value, dict):
                extracted[key] = value
        return extracted

    def _iter_command_nodes(self, node: Dict, path: str):
        """Yield (path, definition) for every executable command node."""
        if not isinstance(node, dict):
            return

        if "command" in node:
            yield path, node

        for key, value in node.items():
            if key in self._node_reserved:
                continue
            if isinstance(value, dict):
                child_path = f"{path}.{key}" if path else key
                yield from self._iter_command_nodes(value, child_path)

    @staticmethod
    def _command_to_text(command_value: Any) -> str:
        """Normalize command value to text for lightweight validation checks."""
        if isinstance(command_value, list):
            return "\n".join(str(item) for item in command_value)
        if isinstance(command_value, str):
            return command_value
        return ""
    
    def validate_file(self, filepath: str, verbose: bool = False) -> Tuple[bool, List[str], List[str]]:
        """Validate an XTS file.
        
        Args:
            filepath: Path to .xts file
            verbose: Show detailed validation info
            
        Returns:
            Tuple of (is_valid, errors, warnings)
        """
        errors = []
        warnings = []
        
        # Special case: hello_world.xts is always valid
        if os.path.basename(filepath) == "hello_world.xts":
            return True, [], []

        # Check file exists
        if not os.path.exists(filepath):
            errors.append(f"File not found: {filepath}")
            return False, errors, warnings

        # Check extension
        if not filepath.endswith('.xts'):
            warnings.append(f"File should have .xts extension")

        # Parse YAML
        try:
            with open(filepath) as f:
                config = yaml.load(f, SafeLoader)
        except yaml.YAMLError as e:
            errors.append(f"YAML parsing error: {e}")
            return False, errors, warnings

        if config is None:
            errors.append("Empty configuration file")
            return False, errors, warnings

        # JSON Schema validation (best-effort; semantic validation is authoritative)
        if JSONSCHEMA_AVAILABLE and self.schema:
            try:
                jsonschema.validate(instance=config, schema=self.schema)
                if verbose:
                    info("✓ Schema validation passed")
            except jsonschema.ValidationError as e:
                warnings.append(f"Schema validation warning: {e.message}")
                if e.path:
                    warnings.append(f"  Location: {' -> '.join(str(p) for p in e.path)}")

        # Additional semantic validation
        self._validate_commands(config, errors, warnings, verbose)
        self._validate_functions(config, errors, warnings, verbose)
        self._validate_placeholders(config, errors, warnings, verbose)
        self._check_best_practices(config, errors, warnings, verbose)
        
        return len(errors) == 0, errors, warnings
    
    def _validate_commands(self, config: Dict, errors: List[str], warnings: List[str], verbose: bool):
        """Validate command definitions."""
        commands = self._extract_commands(config)
        
        if not commands:
            warnings.append("No commands defined")
            return
        
        validated_count = 0
        
        for cmd_name, cmd_def in commands.items():
            # Check command name
            if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', cmd_name):
                errors.append(f"Invalid command name '{cmd_name}' - must start with letter/underscore")

            if not isinstance(cmd_def, dict):
                errors.append(f"Command '{cmd_name}' must be a mapping")
                continue

            leaf_count = 0
            for full_name, leaf_def in self._iter_command_nodes(cmd_def, cmd_name):
                leaf_count += 1
                validated_count += 1

                command_value = leaf_def.get('command')
                command_text = self._command_to_text(command_value)
                if not command_text.strip():
                    errors.append(f"Command '{full_name}' has empty command string")

                args = leaf_def.get('args', [])
                if not isinstance(args, list):
                    errors.append(f"Command '{full_name}': 'args' must be a list")
                    continue

                seen_optional = False
                for i, arg in enumerate(args):
                    if not isinstance(arg, dict):
                        errors.append(f"Command '{full_name}': arg index {i} must be a mapping")
                        continue

                    arg_name = arg.get('name', f'arg_{i}')

                    # Check required comes before optional
                    is_required = arg.get('required', True)
                    if not is_required:
                        seen_optional = True
                    elif seen_optional:
                        warnings.append(f"Command '{full_name}': Required arg '{arg_name}' after optional arg")

                    # Check placeholder exists in command
                    placeholder = f"{{{{{arg_name}}}}}"
                    if placeholder not in command_text:
                        warnings.append(f"Command '{full_name}': Arg '{arg_name}' not used in command")

            if leaf_count == 0:
                errors.append(f"Command '{cmd_name}' missing 'command' field")

        if verbose:
            info(f"Validating {validated_count} command(s)")
    
    def _validate_functions(self, config: Dict, errors: List[str], warnings: List[str], verbose: bool):
        """Validate function definitions."""
        functions = config.get('functions', {})
        
        if not functions:
            return
        
        if verbose:
            info(f"Validating {len(functions)} function(s)")
        
        for func_name, func_def in functions.items():
            if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', func_name):
                errors.append(f"Invalid function name '{func_name}'")
            
            if 'command' not in func_def:
                errors.append(f"Function '{func_name}' missing 'command' field")
    
    def _validate_placeholders(self, config: Dict, errors: List[str], warnings: List[str], verbose: bool):
        """Validate placeholder usage."""
        commands = self._extract_commands(config)
        functions = config.get('functions', {})
        
        # Build set of defined functions (user-defined + standard library)
        from .standard_functions import get_standard_function_names
        func_names = get_standard_function_names() | set(functions.keys())
        
        for top_name, top_def in commands.items():
            if not isinstance(top_def, dict):
                continue
            for cmd_name, cmd_def in self._iter_command_nodes(top_def, top_name):
            # Find all placeholders in command
                command_str = self._command_to_text(cmd_def.get('command', ''))
                placeholders = re.findall(r'\{\{([a-zA-Z_][a-zA-Z0-9_]*)\}\}', command_str)
            
            # Build set of defined args
                arg_names = {
                    arg.get('name')
                    for arg in cmd_def.get('args', [])
                    if isinstance(arg, dict) and arg.get('name')
                }
            
            # Check each placeholder
                for placeholder in placeholders:
                    if placeholder not in arg_names and placeholder not in func_names:
                        errors.append(
                            f"Command '{cmd_name}': Unknown placeholder '{{{{{placeholder}}}}}' "
                            f"(not in args or functions)"
                        )
            
            # Check formatter
                if 'formatter' in cmd_def and isinstance(cmd_def['formatter'], str):
                    formatter = cmd_def['formatter']
                    formatter_placeholders = re.findall(r'\{\{([a-zA-Z_][a-zA-Z0-9_]*)\}\}', formatter)
                    for placeholder in formatter_placeholders:
                        if placeholder not in func_names:
                            errors.append(
                                f"Command '{cmd_name}': Formatter references unknown function '{{{{{placeholder}}}}}'"
                            )
    
    def _check_best_practices(self, config: Dict, errors: List[str], warnings: List[str], verbose: bool):
        """Check best practices and style guidelines."""
        commands = self._extract_commands(config)

        for top_name, top_def in commands.items():
            if not isinstance(top_def, dict):
                continue
            for cmd_name, cmd_def in self._iter_command_nodes(top_def, top_name):
            # Check for description
                if 'description' not in cmd_def:
                    warnings.append(f"Command '{cmd_name}' missing description")
            
            # Check arg descriptions
                for arg in cmd_def.get('args', []):
                    if isinstance(arg, dict) and 'description' not in arg and 'name' in arg:
                        warnings.append(f"Command '{cmd_name}': Arg '{arg['name']}' missing description")
            
            # Check for very long commands
                command_str = self._command_to_text(cmd_def.get('command', ''))
                if len(command_str) > 500:
                    warnings.append(
                        f"Command '{cmd_name}': Very long command ({len(command_str)} chars) - "
                        "consider using a script file"
                    )
            
            # Check for inline python without python3
                if 'python -c' in command_str and 'python3 -c' not in command_str:
                    warnings.append(f"Command '{cmd_name}': Use 'python3' instead of 'python' for compatibility")


def validate_command(filepath: str, verbose: bool = False, json_output: bool = False) -> int:
    """Validate an XTS file and print results.
    
    Args:
        filepath: Path to .xts file
        verbose: Show detailed validation info
        json_output: Output results as JSON
        
    Returns:
        Exit code (0 = valid, 1 = invalid)
    """
    validator = XTSValidator()
    is_valid, errors_list, warnings_list = validator.validate_file(filepath, verbose)

    def print_invalid_line(err_msg):
        # Try to extract command name or line number from error message
        import re
        # Match command 'name' or Command 'name'
        m = re.search(r"[Cc]ommand '([\w\.]+)'", err_msg)
        if not m:
            return
        cmd_path = m.group(1)
        # Try to find and print the relevant line from the file
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            # Print lines containing the command path as a key
            found = False
            for i, line in enumerate(lines):
                if re.match(rf"^\s*{re.escape(cmd_path)}\s*:", line):
                    print(f"    > {line.rstrip()}")
                    # Optionally print the next few lines for context
                    for j in range(1, 4):
                        if i + j < len(lines):
                            print(f"      {lines[i+j].rstrip()}")
                    found = True
                    break
            if not found:
                # Try to find as a nested key (e.g., parent.child)
                parts = cmd_path.split('.')
                for i, line in enumerate(lines):
                    if all(part in line for part in parts):
                        print(f"    > {line.rstrip()}")
                        break
        except Exception:
            pass

    if json_output:
        result = {
            "file": filepath,
            "valid": is_valid,
            "errors": errors_list,
            "warnings": warnings_list
        }
        print(json.dumps(result, indent=2))
    else:
        # Human-readable output
        print(f"\nValidating: {filepath}\n")

        if errors_list:
            error(f"✗ Found {len(errors_list)} error(s):")
            for err in errors_list:
                print(f"  • {err}")
                print_invalid_line(err)
            print()

        if warnings_list:
            warning(f"⚠ Found {len(warnings_list)} warning(s):")
            for warn in warnings_list:
                print(f"  • {warn}")
            print()

        if is_valid and not warnings_list:
            success(f"✓ Validation passed - file is valid!")
        elif is_valid:
            success(f"✓ Validation passed with {len(warnings_list)} warning(s)")
        else:
            error("✗ Validation failed")

    return 0 if is_valid else 1


def main():
    """CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Validate XTS configuration files")
    parser.add_argument('file', help='Path to .xts file to validate')
    parser.add_argument('-v', '--verbose', action='store_true', help='Show detailed validation info')
    parser.add_argument('--json', action='store_true', help='Output results as JSON')
    
    args = parser.parse_args()
    
    if not JSONSCHEMA_AVAILABLE:
        warning("jsonschema package not installed - install with: pip install jsonschema")
        print()
    
    exit_code = validate_command(args.file, args.verbose, args.json)
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
